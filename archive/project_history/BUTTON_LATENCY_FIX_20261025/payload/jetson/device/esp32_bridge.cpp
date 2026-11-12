// Read-only serial owner. There is deliberately NO serial write/command API.
#include "telemetry.h"
#include "feed_policy.h"
#include "decision_logic.h"
#include <sqlite3.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/timex.h>
#include <termios.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <glob.h>
#include <signal.h>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <regex>

namespace {
using namespace forcat;
volatile sig_atomic_t stopping=0;
void stop(int){stopping=1;}
uint64_t mono(){return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());}
int64_t wall(){return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();}
std::string readFile(const std::string& p){std::ifstream in(p);std::string s;std::getline(in,s);return s;}
std::string utc(){const auto t=std::time(nullptr);std::tm tm{};gmtime_r(&t,&tm);char out[40];std::strftime(out,sizeof(out),"%Y-%m-%dT%H:%M:%SZ",&tm);return out;}
struct Options {
    std::string device="auto",usb_serial,db="jetson/data/events.db",log="evidence/esp32_bridge.jsonl";
    unsigned baud=115200,stale_ms=3000,reconnect_ms=2000,seconds=0;
    NearConfig near;
    WaterConfig water;
};
unsigned argument(const std::string& value,unsigned low,unsigned high){
    size_t end=0;auto n=std::stoul(value,&end);if(end!=value.size() || n<low || n>high)throw std::invalid_argument("numeric option out of range");return static_cast<unsigned>(n);
}
double distanceArgument(const std::string& value){size_t end=0;double n=std::stod(value,&end);if(end!=value.size() || !std::isfinite(n) || n<=0 || n>400)throw std::invalid_argument("distance option out of range");return n;}
Options options(int argc,char** argv){
    Options o;
    for(int i=1;i<argc;++i){std::string k=argv[i];if(i+1==argc)throw std::invalid_argument("option needs value");std::string v=argv[++i];
        if(k=="--device")o.device=v;else if(k=="--usb-serial")o.usb_serial=v;else if(k=="--db")o.db=v;
        else if(k=="--log")o.log=v;else if(k=="--baud")o.baud=argument(v,9600,230400);
        else if(k=="--stale-ms")o.stale_ms=argument(v,500,60000);else if(k=="--reconnect-ms")o.reconnect_ms=argument(v,100,30000);
        else if(k=="--seconds")o.seconds=argument(v,1,86400);
        else if(k=="--near-cm")o.near.distance_cm=distanceArgument(v);
        else if(k=="--near-stable-ms")o.near.stable_ms=argument(v,100,10000);
        else if(k=="--water-low-cm")o.water.low_distance_cm=distanceArgument(v);
        else if(k=="--water-target-cm")o.water.target_distance_cm=distanceArgument(v);
        else throw std::invalid_argument("unknown option "+k);
    }
    if(o.baud!=9600 && o.baud!=57600 && o.baud!=115200 && o.baud!=230400)throw std::invalid_argument("unsupported baud");
    if((o.water.low_distance_cm || o.water.target_distance_cm) && !o.water.configured())throw std::invalid_argument("water requires reviewed LOW > TARGET > 0 geometry");
    return o;
}
struct Device {std::string path,vid,pid,serial;};
Device discover(const Options& o){
    if(o.device!="auto")return {o.device,"","",""};
    glob_t paths{};glob("/sys/class/tty/ttyACM*",0,nullptr,&paths);glob("/sys/class/tty/ttyUSB*",GLOB_APPEND,nullptr,&paths);
    std::vector<Device> candidates;
    for(size_t i=0;i<paths.gl_pathc;++i){
        std::string tty=paths.gl_pathv[i];char resolved[4096];
        if(!realpath((tty+"/device").c_str(),resolved))continue;
        std::string parent=resolved;
        for(int depth=0;depth<10 && parent.size()>1;++depth){
            auto vid=readFile(parent+"/idVendor"),pid=readFile(parent+"/idProduct"),serial=readFile(parent+"/serial");
            if((vid=="1a86" && (pid=="55d3" || pid=="7523")) || (vid=="303a" && pid=="1001")){
                if(o.usb_serial.empty() || o.usb_serial==serial)candidates.push_back({"/dev/"+tty.substr(tty.find_last_of('/')+1),vid,pid,serial});
                break;
            }
            parent=parent.substr(0,parent.find_last_of('/'));
        }
    }
    globfree(&paths);
    // Never select an arbitrary board when multiple supported devices exist.
    return candidates.size()==1?candidates.front():Device{};
}
struct StorageBusy:std::runtime_error {using std::runtime_error::runtime_error;};
class Database {
    sqlite3* db_=nullptr;
    void exec(const char* sql){char* error=nullptr;int rc=sqlite3_exec(db_,sql,nullptr,nullptr,&error);if(rc!=SQLITE_OK){std::string message=error?error:"sqlite";sqlite3_free(error);if(rc==SQLITE_BUSY || rc==SQLITE_LOCKED)throw StorageBusy(message);throw std::runtime_error(message);}}
    void bindExec(const char* sql,const std::vector<std::string>& fields){
        sqlite3_stmt* s=nullptr;
        int prepared=sqlite3_prepare_v2(db_,sql,-1,&s,nullptr);
        if(prepared!=SQLITE_OK){if(prepared==SQLITE_BUSY || prepared==SQLITE_LOCKED)throw StorageBusy(sqlite3_errmsg(db_));throw std::runtime_error(sqlite3_errmsg(db_));}
        for(size_t i=0;i<fields.size();++i)sqlite3_bind_text(s,static_cast<int>(i+1),fields[i].c_str(),-1,SQLITE_TRANSIENT);
        const int code=sqlite3_step(s);sqlite3_finalize(s);if(code!=SQLITE_DONE){if(code==SQLITE_BUSY || code==SQLITE_LOCKED)throw StorageBusy(sqlite3_errmsg(db_));throw std::runtime_error(sqlite3_errmsg(db_));}
    }
public:
    explicit Database(const std::string& path){
        if(sqlite3_open_v2(path.c_str(),&db_,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_FULLMUTEX,nullptr)!=SQLITE_OK)
            throw std::runtime_error("cannot open canonical database");
        sqlite3_busy_timeout(db_,200);
        exec("PRAGMA journal_mode=WAL; PRAGMA journal_size_limit=4194304;");
        // Additive tables: existing PRAGMA user_version=2 and API tables untouched.
        exec("CREATE TABLE IF NOT EXISTS esp32_bridge_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);"
             "CREATE TABLE IF NOT EXISTS esp32_latest(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL);"
             "CREATE TABLE IF NOT EXISTS esp32_events(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,occurred_at TEXT NOT NULL,body TEXT NOT NULL);"
             "CREATE TABLE IF NOT EXISTS feed_dry_run_requests(request_id TEXT PRIMARY KEY,body TEXT NOT NULL,decision TEXT);");
        sqlite3_stmt* s=nullptr;sqlite3_prepare_v2(db_,"SELECT value FROM esp32_bridge_meta WHERE key='schema_version'",-1,&s,nullptr);
        const int rc=sqlite3_step(s);const bool supported=rc==SQLITE_DONE || (rc==SQLITE_ROW && std::string(reinterpret_cast<const char*>(sqlite3_column_text(s,0)))=="1");
        sqlite3_finalize(s);if(!supported)throw std::runtime_error("unsupported bridge schema");
        exec("INSERT OR IGNORE INTO esp32_bridge_meta VALUES('schema_version','1')");
    }
    ~Database(){if(db_)sqlite3_close(db_);}
    void latest(const std::string& body){bindExec("INSERT OR REPLACE INTO esp32_latest(id,body) VALUES(1,?)",{body});}
    std::vector<std::pair<std::string,std::string>> pendingRequests(){
        std::vector<std::pair<std::string,std::string>> result;sqlite3_stmt* s=nullptr;
        if(sqlite3_prepare_v2(db_,"SELECT request_id,body FROM feed_dry_run_requests WHERE decision IS NULL ORDER BY rowid LIMIT 4",-1,&s,nullptr)!=SQLITE_OK)return result;
        while(sqlite3_step(s)==SQLITE_ROW){
            const char* id=reinterpret_cast<const char*>(sqlite3_column_text(s,0));const char* body=reinterpret_cast<const char*>(sqlite3_column_text(s,1));
            if(id && body && sqlite3_column_bytes(s,0)<=96 && sqlite3_column_bytes(s,1)<=2048)result.emplace_back(id,body);
        }
        sqlite3_finalize(s);return result;
    }
    void decision(const std::string& id,json_object* value){bindExec("UPDATE feed_dry_run_requests SET decision=? WHERE request_id=? AND decision IS NULL",{encode(value),id});}
    std::string species(uint64_t now,const std::string& boot){
        sqlite3_stmt* s=nullptr;
        if(sqlite3_prepare_v2(db_,"SELECT body FROM ai_latest WHERE id=1",-1,&s,nullptr)!=SQLITE_OK)return "UNKNOWN";
        std::string body;
        if(sqlite3_step(s)==SQLITE_ROW){const char* p=reinterpret_cast<const char*>(sqlite3_column_text(s,0));if(p && sqlite3_column_bytes(s,0)<=4096)body=p;}
        sqlite3_finalize(s);
        try{auto value=own(json_tokener_parse(body.c_str()));
            if(text(value.get(),"health")!="ONLINE" || text(value.get(),"host_boot_id")!=boot)return "UNKNOWN";
            auto stamp=field(value.get(),"updated_monotonic_ms");if(!stamp || !json_object_is_type(stamp,json_type_int))return "UNKNOWN";
            int64_t then=json_object_get_int64(stamp);if(then<0 || static_cast<uint64_t>(then)>now || now-static_cast<uint64_t>(then)>3000)return "UNKNOWN";
            auto species=text(value.get(),"classification");return species=="CAT"||species=="DOG"||species=="NONE"?species:"UNKNOWN";
        }catch(const std::invalid_argument&){return "UNKNOWN";}
    }
    void event(const std::string& kind,json_object* body){
        exec("BEGIN IMMEDIATE");
        try{bindExec("INSERT INTO esp32_events(kind,occurred_at,body) VALUES(?,?,?)",{kind,utc(),encode(body)});
            exec("DELETE FROM esp32_events WHERE seq NOT IN (SELECT seq FROM esp32_events ORDER BY seq DESC LIMIT 1000);COMMIT;");}
        catch(...){sqlite3_exec(db_,"ROLLBACK",nullptr,nullptr,nullptr);throw;}
    }
};
class Log {
    std::string path_;
public:
    explicit Log(std::string path):path_(std::move(path)){}
    void event(const std::string& kind,json_object* body){
        struct stat st{};if(stat(path_.c_str(),&st)==0 && st.st_size>=1024*1024){
            // Fixed ring: at most current + two rotated 1MiB files.
            rename((path_+".1").c_str(),(path_+".2").c_str());rename(path_.c_str(),(path_+".1").c_str());
        }
        auto item=own(json_object_new_object());put(item.get(),"timestamp",utc());put(item.get(),"kind",kind);
        json_object_object_add(item.get(),"details",json_object_get(body));
        std::ofstream out(path_,std::ios::app);if(!out)throw std::runtime_error("log path unavailable");out<<encode(item.get())<<'\n';
    }
};
int openSerial(const std::string& path,unsigned baud){
    int fd=open(path.c_str(),O_RDONLY|O_NOCTTY|O_NONBLOCK|O_CLOEXEC);
    if(fd<0)return -1;
    struct stat st{};termios tty{};
    if(fstat(fd,&st)<0 || !S_ISCHR(st.st_mode) || !isatty(fd) || flock(fd,LOCK_EX|LOCK_NB)<0 ||
       ioctl(fd,TIOCEXCL)<0 || tcgetattr(fd,&tty)<0){close(fd);return -1;}
    cfmakeraw(&tty);tty.c_cflag|=CLOCAL|CREAD;tty.c_cflag&=~(HUPCL|CRTSCTS);
    tty.c_cc[VMIN]=0;tty.c_cc[VTIME]=0;
    speed_t speed=baud==9600?B9600:baud==57600?B57600:baud==230400?B230400:B115200;
    cfsetispeed(&tty,speed);cfsetospeed(&tty,speed);
    if(tcsetattr(fd,TCSANOW,&tty)<0){ioctl(fd,TIOCNXCL);close(fd);return -1;}
    return fd;
}
void closeSerial(int& fd){if(fd>=0){ioctl(fd,TIOCNXCL);close(fd);fd=-1;}}
int bridge(const Options& o){
    const std::string lockpath=o.db+"-esp32.lock";
    const int lockfd=open(lockpath.c_str(),O_CREAT|O_RDWR|O_CLOEXEC,0600);
    if(lockfd<0 || flock(lockfd,LOCK_EX|LOCK_NB)<0)throw std::runtime_error("another canonical bridge owns this database");
    Database db(o.db);Log log(o.log);LineFramer framer;FeedArbiter arbiter;TimeGate time;
    AutoCatGate auto_gate(o.near);FoodBehaviorFsm behavior;WaterDryRun water_policy(o.water);
    uint64_t auto_candidates=0;
    const auto started=mono();const std::string boot_id=readFile("/proc/sys/kernel/random/boot_id");
    const std::string instance=boot_id+":"+std::to_string(getpid())+":"+std::to_string(started);
    uint64_t last_rx=0,last_progress=0,last_publish=0,last_housekeeping=0,retry=0,connection_at=0,last_sample=0;
    uint64_t parse_errors=0,valid_reports=0,open_errors=0,connections=0,reconnects=0,reboots=0,noise_lines=0,frozen_reports=0;
    bool bad=false,unsafe=false,have_previous=false;int fd=-1;Device device;
    bool state_dirty=false;
    uint32_t previous_uptime=0,previous_button=0;bool previous_had_button=false;
    Json latest;std::string last_received_utc,previous_health,sensor_signature,unsafe_report;
    std::map<std::string,Json> queue_decisions;
    uint64_t storage_errors=0;
    auto event=[&](const std::string& kind,json_object* details){try{db.event(kind,details);}catch(const StorageBusy&){++storage_errors;}log.event(kind,details);};
    auto simple=[&](const std::string& kind,const std::string& reason){auto j=own(json_object_new_object());put(j.get(),"reason",reason);event(kind,j.get());};
    auto buttonRequest=[&](uint32_t count,uint32_t stamp){
        FeedRequest request{instance+":"+std::to_string(reboots)+":"+std::to_string(count),"MANUAL","BUTTON",FEED_TARGET_GRAMS};
        request.requested_at_unix_ms=wall();
        FeedEvidence evidence;evidence.time_valid=time.valid();evidence.telemetry_safe=true;
        auto decision=arbiter.evaluate(request,evidence,mono());
        auto item=own(json_object_new_object());put(item.get(),"request_id",request.id);put(item.get(),"source","MANUAL");
        put(item.get(),"manual_source","BUTTON");put(item.get(),"event","MANUAL_BUTTON_FEED_REQUEST");
        number(item.get(),"target_grams",true,request.target_grams);json_object_object_add(item.get(),"actual_dispensed_grams",nullptr);
        integer(item.get(),"requested_at_unix_ms",request.requested_at_unix_ms);put(item.get(),"time_valid",time.valid());
        put(item.get(),"actuator_execution",false);put(item.get(),"reason",decision.reason);
        put(item.get(),"qualification_reason",decision.qualification_reason);integer(item.get(),"button_count",count);
        integer(item.get(),"device_press_ms",stamp);event("feed_request_dry_run",item.get());
    };
    const std::regex button_line("^MANUAL_BUTTON_FEED_REQUEST count=([0-9]{1,10}) monotonic_ms=([0-9]{1,10}) actuator_blocked=true$");
    auto onLine=[&](const std::string& line){
        if(unsafe)return;
        if(line[0]!='{'){
            std::smatch match;
            if(std::regex_match(line,match,button_line) && have_previous && previous_had_button && !bad && fd>=0 &&
               mono()-last_rx<=o.stale_ms && mono()-last_progress<=o.stale_ms){
                const auto count=std::stoull(match[1]),stamp=std::stoull(match[2]);
                if(count<=UINT32_MAX && stamp<=UINT32_MAX && count>previous_button &&
                   static_cast<uint32_t>(stamp)-previous_uptime<=o.stale_ms){
                    if(count==static_cast<uint64_t>(previous_button)+1)buttonRequest(static_cast<uint32_t>(count),static_cast<uint32_t>(stamp));
                    else simple("system_health_event","BUTTON_EVENT_GAP_NOT_REPLAYED");
                    previous_button=static_cast<uint32_t>(count);
                    // The accepted press-edge line is a real button observation.
                    // Update only the button, not JSON freshness/other sensors.
                    if(latest){
                        auto button=field(field(latest.get(),"sensors"),"button");
                        put(button,"pressed",true);integer(button,"button_raw_level",0);
                        integer(button,"button_debounced_level",0);integer(button,"request_count",static_cast<int64_t>(count));
                        integer(button,"last_press_ms",static_cast<int64_t>(stamp));
                        put(button,"state_source","PRESS_EVENT");integer(button,"state_device_ms",static_cast<int64_t>(stamp));
                        state_dirty=true;
                    }
                }
            }else ++noise_lines;
            return;
        }
        try{
            auto t=parseTelemetry(line);const auto now=mono();
            bool reboot=have_previous && t.uptime<previous_uptime && previous_uptime-t.uptime<0x80000000u;
            if(t.has_button && previous_had_button && !reboot && t.button_count<previous_button)
                throw std::invalid_argument("button counter regressed without reboot");
            if(!have_previous || t.uptime!=previous_uptime)last_progress=now;else ++frozen_reports;
            if(reboot){++reboots;auto_gate.reset();simple("system_health_event","ESP32_UPTIME_RESET");}
            auto sensors_for_decision=field(t.normalized.get(),"sensors");
            auto near_sensor=field(sensors_for_decision,"approach");double near_distance=0;
            bool near_valid=nullableNumber(near_sensor,"distance_cm",near_distance) && boolean(near_sensor,"distance_valid");
            const auto ai_species=db.species(now,boot_id);
            if(auto_gate.update(ai_species,true,near_valid,near_distance,t.uptime,now)){
                ++auto_candidates;
                FeedRequest request{instance+":AUTO:"+std::to_string(auto_candidates),"AUTO_CAT","",FEED_TARGET_GRAMS};
                request.requested_at_unix_ms=wall();
                FeedEvidence evidence;evidence.species=ai_species;evidence.observations_fresh=true;
                evidence.near_confirmed_stable=true;evidence.telemetry_safe=true;evidence.time_valid=time.valid();
                auto decision=arbiter.evaluate(request,evidence,now);
                auto item=own(json_object_new_object());put(item.get(),"request_id",request.id);put(item.get(),"source","AUTO_CAT");
                integer(item.get(),"requested_at_unix_ms",request.requested_at_unix_ms);number(item.get(),"target_grams",true,FEED_TARGET_GRAMS);
                json_object_object_add(item.get(),"actual_dispensed_grams",nullptr);put(item.get(),"actuator_execution",false);
                put(item.get(),"reason",decision.reason);put(item.get(),"qualification_reason",decision.qualification_reason);event("feed_request_dry_run",item.get());
            }
            behavior.update(ai_species=="CAT",auto_gate.stable(),false,false,0,now);
            auto water_sensor=field(sensors_for_decision,"water_operational");double water_distance=0;
            const bool water_valid=nullableNumber(water_sensor,"distance_cm",water_distance) && boolean(water_sensor,"distance_valid");
            water_policy.update(water_valid,water_distance,true,now); // preview only, no pump interface
            if(t.has_button && previous_had_button && !reboot && t.button_count>previous_button){
                if(t.button_count==previous_button+1){
                    buttonRequest(t.button_count,counter(field(sensors_for_decision,"button"),"last_press_ms"));
                }else simple("system_health_event","BUTTON_COUNTER_GAP_NOT_REPLAYED");
            }
            previous_uptime=t.uptime;previous_button=t.button_count;previous_had_button=t.has_button;have_previous=true;
            auto signature=own(json_object_new_object());auto sensors=field(t.normalized.get(),"sensors");
            for(auto role:{"oled","hx711","approach","water_operational"})put(signature.get(),role,text(field(sensors,role),"health"));
            copy(signature.get(),"pir_motion",field(sensors,"pir"),"motion");
            auto sig=encode(signature.get());if(sig!=sensor_signature){event("sensor_state",signature.get());sensor_signature=sig;}
            latest=t.normalized;last_rx=now;last_received_utc=utc();bad=false;++valid_reports;state_dirty=true;
            if(now-last_sample>=5000){event("telemetry_sample",latest.get());last_sample=now;}
        }catch(const UnsafeTelemetry& error){unsafe=true;bad=true;state_dirty=true;unsafe_report=line;++parse_errors;simple("system_health_event",error.what());closeSerial(fd);}
         catch(const std::invalid_argument& error){bad=true;state_dirty=true;++parse_errors;if(parse_errors<=5 || parse_errors%100==0)simple("telemetry_parse_error",error.what());}
    };
    simple("system_health_event","BRIDGE_START_READ_ONLY_UNATTENDED_SAFE_MODE");
    while(!stopping && (!o.seconds || mono()-started<static_cast<uint64_t>(o.seconds)*1000)){
        auto now=mono();
        if(fd<0 && !unsafe && now>=retry){
            device=discover(o);if(!device.path.empty())fd=openSerial(device.path,o.baud);
            if(fd>=0){++connections;if(connections>1)++reconnects;connection_at=now;framer.clear();state_dirty=true;simple("serial_connection",device.path);}
            else {++open_errors;if(open_errors==1 || open_errors%30==0)simple("serial_disconnected",device.path.empty()?"NO_UNAMBIGUOUS_ESP32_USB_DEVICE":"OPEN_FAILED_BUSY_OR_PERMISSION");}
            retry=now+o.reconnect_ms;
        }
        if(fd>=0){
            pollfd p{fd,POLLIN,0};int rc=poll(&p,1,100);
            if(rc<0 && errno!=EINTR)throw std::runtime_error("serial poll failed");
            if(rc>0 && (p.revents&(POLLERR|POLLHUP|POLLNVAL))){closeSerial(fd);framer.clear();state_dirty=true;simple("serial_disconnected","USB_HUP_OR_ERROR");retry=mono()+o.reconnect_ms;}
            else if(rc>0 && (p.revents&POLLIN)){
                char bytes[1024];ssize_t n=read(fd,bytes,sizeof(bytes));
                if(n>0)framer.feed(bytes,static_cast<size_t>(n),onLine);
                else if(n==0 || (n<0 && errno!=EAGAIN && errno!=EINTR)){closeSerial(fd);framer.clear();state_dirty=true;simple("serial_disconnected","READ_ERROR_OR_EOF");retry=mono()+o.reconnect_ms;}
            }
        }else poll(nullptr,0,100);
        now=mono();
        if(state_dirty || now-last_publish>=1000){
            const bool periodic=now-last_housekeeping>=1000;
            if(periodic){
                timex tx{};const int result=adjtimex(&tx);time.update(wall(),now,result>=0 && result!=TIME_ERROR && !(tx.status&STA_UNSYNC));
                last_housekeeping=now;
            }
            const std::string health=unsafe?"ESP32_BAD_TELEMETRY":fd<0?"ESP32_DISCONNECTED":bad?"ESP32_BAD_TELEMETRY":
                last_rx && last_rx>=connection_at && now-last_rx<=o.stale_ms && now-last_progress<=o.stale_ms?"ESP32_CONNECTED":"ESP32_STALE";
            if(health!="ESP32_CONNECTED"){
                auto_gate.reset();behavior.update(false,false,false,false,0,now);water_policy.update(false,0,false,now);
            }
            if(periodic)for(const auto& pending:db.pendingRequests()){
                if(!queue_decisions.count(pending.first)){
                    auto result=own(json_object_new_object());put(result.get(),"request_id",pending.first);
                    put(result.get(),"status","DRY_RUN_BLOCKED");put(result.get(),"reason","UNATTENDED_SAFE_MODE");
                    put(result.get(),"actuator_execution",false);json_object_object_add(result.get(),"actual_dispensed_grams",nullptr);
                    try{
                        auto body=own(json_tokener_parse(pending.second.c_str()));double target=0;
                        if(text(body.get(),"request_id")!=pending.first || !nullableNumber(body.get(),"target_grams",target))throw std::invalid_argument("bad inbox identity/target");
                        FeedRequest request{pending.first,text(body.get(),"source"),text(body.get(),"sub_source"),target};
                        FeedEvidence evidence;evidence.time_valid=time.valid();evidence.telemetry_safe=health=="ESP32_CONNECTED";
                        evidence.species=db.species(now,boot_id);evidence.observations_fresh=evidence.species!="UNKNOWN";
                        evidence.near_confirmed_stable=auto_gate.stable();
                        auto decision=arbiter.evaluate(request,evidence,now);
                        put(result.get(),"source",request.source);put(result.get(),"sub_source",request.manual_source);
                        number(result.get(),"target_grams",true,target);put(result.get(),"qualified",decision.qualified);
                        put(result.get(),"qualification_reason",decision.qualification_reason);
                    }catch(const std::invalid_argument&){put(result.get(),"qualified",false);put(result.get(),"qualification_reason","INVALID_REQUEST");}
                    queue_decisions[pending.first]=result;
                }
                try{auto result=queue_decisions.at(pending.first);db.decision(pending.first,result.get());event("feed_request_dry_run",result.get());queue_decisions.erase(pending.first);}
                catch(const StorageBusy&){++storage_errors;}
            }
            if(health!=previous_health){simple("system_health_event",health);previous_health=health;}
            auto state=own(json_object_new_object());put(state.get(),"schema_version","esp32_bridge_v1");put(state.get(),"health",health);
            put(state.get(),"serial_connected",fd>=0);put(state.get(),"device",device.path);put(state.get(),"usb_vid",device.vid);
            put(state.get(),"usb_pid",device.pid);put(state.get(),"usb_serial",device.serial);integer(state.get(),"baud",o.baud);
            put(state.get(),"host_boot_id",boot_id);put(state.get(),"updated_at",utc());integer(state.get(),"updated_monotonic_ms",static_cast<int64_t>(now));
            integer(state.get(),"last_rx_monotonic_ms",static_cast<int64_t>(last_rx));
            if(last_rx)put(state.get(),"last_received_at",last_received_utc);else json_object_object_add(state.get(),"last_received_at",nullptr);
            put(state.get(),"time_valid",time.valid());put(state.get(),"actuator_execution",false);put(state.get(),"serial_tx_enabled",false);
            put(state.get(),"unsafe_telemetry_latched",unsafe);
            auto decisions=json_object_new_object();json_object_object_add(state.get(),"decisions",decisions);
            put(decisions,"mode","DRY_RUN_ONLY");put(decisions,"near_configured",auto_gate.configured());
            number(decisions,"near_threshold_cm",auto_gate.configured(),o.near.distance_cm);
            put(decisions,"near_stable",auto_gate.stable());integer(decisions,"auto_candidates",static_cast<int64_t>(auto_candidates));
            put(decisions,"food_behavior",name(behavior.state()));put(decisions,"eating_grams_validated",false);
            json_object_object_add(decisions,"consumed_grams",nullptr);
            put(decisions,"water_request_preview",water_policy.requested());put(decisions,"water_reason",water_policy.reason());
            put(decisions,"actuator_execution",false);put(decisions,"scheduled_time_valid",time.valid());
            if(unsafe)put(state.get(),"unsafe_report_raw",unsafe_report);
            auto stats=json_object_new_object();json_object_object_add(state.get(),"counters",stats);
            integer(stats,"valid_reports",static_cast<int64_t>(valid_reports));integer(stats,"parse_errors",static_cast<int64_t>(parse_errors));
            integer(stats,"oversized_lines",static_cast<int64_t>(framer.oversized));integer(stats,"noise_lines",static_cast<int64_t>(noise_lines));
            integer(stats,"connections",static_cast<int64_t>(connections));integer(stats,"reconnects",static_cast<int64_t>(reconnects));
            integer(stats,"open_errors",static_cast<int64_t>(open_errors));integer(stats,"device_reboots",static_cast<int64_t>(reboots));
            integer(stats,"unchanged_uptime_reports",static_cast<int64_t>(frozen_reports));
            integer(stats,"storage_errors",static_cast<int64_t>(storage_errors));
            json_object_object_add(state.get(),"telemetry",latest?json_object_get(latest.get()):nullptr);
            try{db.latest(encode(state.get()));}catch(const StorageBusy&){++storage_errors;}
            last_publish=now;state_dirty=false;
        }
    }
    closeSerial(fd);simple("system_health_event","BRIDGE_STOP");
    // Publish disconnected even after a short test exits, not a stale ONLINE claim.
    auto stopped=own(json_object_new_object());put(stopped.get(),"health",unsafe?"ESP32_BAD_TELEMETRY":"ESP32_DISCONNECTED");put(stopped.get(),"serial_connected",false);
    put(stopped.get(),"host_boot_id",boot_id);integer(stopped.get(),"updated_monotonic_ms",static_cast<int64_t>(mono()));
    put(stopped.get(),"updated_at",utc());put(stopped.get(),"actuator_execution",false);put(stopped.get(),"serial_tx_enabled",false);
    put(stopped.get(),"unsafe_telemetry_latched",unsafe);put(stopped.get(),"time_valid",false);
    integer(stopped.get(),"last_rx_monotonic_ms",static_cast<int64_t>(last_rx));
    if(last_rx)put(stopped.get(),"last_received_at",last_received_utc);else json_object_object_add(stopped.get(),"last_received_at",nullptr);
    json_object_object_add(stopped.get(),"telemetry",latest?json_object_get(latest.get()):nullptr);db.latest(encode(stopped.get()));
    close(lockfd);return 0;
}
} // namespace
int main(int argc,char** argv){
    signal(SIGINT,stop);signal(SIGTERM,stop);
    try{return bridge(options(argc,argv));}catch(const std::exception& e){std::cerr<<"ESP32_BRIDGE_FATAL "<<e.what()<<'\n';return 1;}
}
