// Observe stdout of the UNMODIFIED existing TensorRT binary. No inference rewrite.
#include "telemetry.h"
#include <sqlite3.h>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>
#include <chrono>
#include <ctime>
#include <fstream>
#include <iostream>
#include <regex>
using namespace forcat;
int main(int argc,char** argv){
    if(argc!=2){std::cerr<<"ai_state_tap CANONICAL_DB (stdin=existing detector stdout)\n";return 2;}
    sqlite3* db=nullptr;
    try{
        std::string dbpath=argv[1];int lock=open((dbpath+"-ai.lock").c_str(),O_CREAT|O_RDWR|O_CLOEXEC,0600);
        if(lock<0 || flock(lock,LOCK_EX|LOCK_NB)<0)throw std::runtime_error("AI state tap already owned");
        if(sqlite3_open(dbpath.c_str(),&db)!=SQLITE_OK)throw std::runtime_error("AI database open");
        sqlite3_busy_timeout(db,100);
        if(sqlite3_exec(db,"CREATE TABLE IF NOT EXISTS ai_latest(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)",nullptr,nullptr,nullptr)!=SQLITE_OK)
            throw std::runtime_error(sqlite3_errmsg(db));
        std::ifstream bootfile("/proc/sys/kernel/random/boot_id");std::string boot;std::getline(bootfile,boot);
        uint64_t storage_errors=0;
        auto save=[&](const std::string& health,const std::string& classification,double confidence,bool has_confidence){
            auto state=own(json_object_new_object());put(state.get(),"health",health);put(state.get(),"classification",classification);
            number(state.get(),"confidence",has_confidence,confidence);put(state.get(),"source","EXISTING_CPP_TENSORRT_STDOUT");
            put(state.get(),"host_boot_id",boot);
            auto now=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
            integer(state.get(),"updated_monotonic_ms",now);
            const auto stamp=std::time(nullptr);std::tm tm{};gmtime_r(&stamp,&tm);char iso[40];std::strftime(iso,sizeof(iso),"%Y-%m-%dT%H:%M:%SZ",&tm);
            put(state.get(),"last_observation_at",iso);put(state.get(),"actuator_execution",false);
            integer(state.get(),"storage_errors",static_cast<int64_t>(storage_errors));
            sqlite3_stmt* statement=nullptr;
            if(sqlite3_prepare_v2(db,"INSERT OR REPLACE INTO ai_latest VALUES(1,?)",-1,&statement,nullptr)!=SQLITE_OK){
                ++storage_errors;if(storage_errors<=5 || storage_errors%100==0)std::cerr<<"AI_STATE_STORAGE "<<sqlite3_errmsg(db)<<'\n';
                return; // Never kill or backpressure the working detector for a cache write.
            }
            const auto body=encode(state.get());sqlite3_bind_text(statement,1,body.c_str(),-1,SQLITE_TRANSIENT);
            int rc=sqlite3_step(statement);sqlite3_finalize(statement);
            if(rc!=SQLITE_DONE){++storage_errors;if(storage_errors<=5 || storage_errors%100==0)std::cerr<<"AI_STATE_STORAGE code="<<rc<<" "<<sqlite3_errmsg(db)<<'\n';}
        };
        save("DISCONNECTED","UNKNOWN",0,false);
        bool contract=false;std::regex detection("(CAT|DOG)=([0-9]+(?:\\.[0-9]+)?)");
        LineFramer framing;char buffer[1024];
        auto line=[&](const std::string& value){
            if(value.find("ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16;")==0){contract=true;return;}
            if(!contract || value.find(" MODE=")==std::string::npos || value.find(" PROCESSED=")==std::string::npos)return;
            if(value.find("NONE MODE=")==0){save("ONLINE","NONE",0,false);return;}
            if(value.find("DETECTIONS ")!=0)return;
            std::string classification="UNKNOWN";double confidence=0;
            for(std::sregex_iterator it(value.begin(),value.end(),detection),end;it!=end;++it){
                const std::string species=(*it)[1];double score=std::stod((*it)[2]);if(!std::isfinite(score)||score<0||score>1)return;
                if(species=="DOG" || classification=="UNKNOWN" || (classification==species && score>confidence)){
                    classification=species;confidence=score;
                }
            }
            if(classification!="UNKNOWN")save("ONLINE",classification,confidence,true);
        };
        ssize_t n;
        while((n=read(STDIN_FILENO,buffer,sizeof(buffer)))>0)framing.feed(buffer,static_cast<size_t>(n),line);
        save("DISCONNECTED","UNKNOWN",0,false);
        sqlite3_close(db);close(lock);return 0;
    }catch(const std::exception& error){std::cerr<<"AI_TAP_ERROR "<<error.what()<<'\n';if(db)sqlite3_close(db);return 1;}
}
