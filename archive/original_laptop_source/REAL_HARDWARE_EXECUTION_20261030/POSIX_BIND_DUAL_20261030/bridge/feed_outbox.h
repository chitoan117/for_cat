#pragma once
#include "telemetry.h"
#include "sole_owner_feed_link.h"
#include <sqlite3.h>
#include <functional>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace forcat_bind {
using namespace forcat;
inline std::string hex(const uint8_t* p,size_t n){static const char* c="0123456789abcdef";std::string s;for(size_t i=0;i<n;++i){s+=c[p[i]>>4];s+=c[p[i]&15];}return s;}
inline std::vector<uint8_t> unhex(const std::string& s){
    if(s.size()%2 || s.size()>uart_v1::MAX_FRAME*2)throw std::invalid_argument("packet bound");
    std::vector<uint8_t> out;for(size_t i=0;i<s.size();i+=2){unsigned value=0;for(unsigned j=0;j<2;++j){const char c=s[i+j];if(c>='0'&&c<='9')value=value*16+unsigned(c-'0');else if(c>='a'&&c<='f')value=value*16+unsigned(c-'a'+10);else throw std::invalid_argument("hex");}out.push_back(static_cast<uint8_t>(value));}return out;
}
class Outbox:public forcat_feed_bridge::Writer,public forcat_feed_bridge::DurableStore {
    sqlite3* db_=nullptr;
    forcat_feed_bridge::Link link_{*this,*this};
    forcat_feed_bridge::Review review_{};
    std::function<size_t(const uint8_t*,size_t)> writer_;
    bool connected_=false,enabled_=false,source_mock_=false,tx_attempted_=false;
    int64_t expires_=0;std::string producer_,review_hash_,error_;
    void sql(const char* s){char* error=nullptr;const int code=sqlite3_exec(db_,s,nullptr,nullptr,&error);if(code!=SQLITE_OK){std::string message=error?error:"SQLite";sqlite3_free(error);throw std::runtime_error(message);}}
    void change(const char* s,const std::vector<std::string>& values){
        sqlite3_stmt* statement=nullptr;if(sqlite3_prepare_v2(db_,s,-1,&statement,nullptr)!=SQLITE_OK)throw std::runtime_error(sqlite3_errmsg(db_));
        for(size_t i=0;i<values.size();++i)sqlite3_bind_text(statement,int(i+1),values[i].c_str(),-1,SQLITE_TRANSIENT);
        const int code=sqlite3_step(statement);sqlite3_finalize(statement);if(code!=SQLITE_DONE)throw std::runtime_error(sqlite3_errmsg(db_));
    }
    bool requestBound(uint32_t id,uint32_t boot,uint32_t origin){
        sqlite3_stmt* s=nullptr;bool ok=false;
        if(sqlite3_prepare_v2(db_,"SELECT boot,origin FROM cl_requests WHERE id=?",-1,&s,nullptr)!=SQLITE_OK)return false;
        sqlite3_bind_int64(s,1,id);if(sqlite3_step(s)==SQLITE_ROW)ok=sqlite3_column_int64(s,0)==boot && sqlite3_column_int64(s,1)==origin;
        sqlite3_finalize(s);return ok;
    }
    bool resultValid(uint32_t id,const uint8_t* p,uint16_t n){
        if(n!=35 || p[0]!=1 || !requestBound(id,feed_link::get32(p+1),feed_link::get32(p+13)) || p[18]>9 || (p[20]&~127u) || feed_link::getFloat(p+23)!=35.f)return false;
        if(p[17]!=0 && p[17]!=1 && p[17]!=3)return false;
        if(bool(p[20]&feed_link::FINAL)!=(p[17]!=0))return false;
        const auto mass=feed_link::getFloat(p+27);
        if(p[17]==1 && (p[18]!=8 || p[19]!=0 || p[20]!=127 || !feed_link::get16(p+21) || !std::isfinite(mass) || mass<30 || mass>40))return false;
        return !(p[20]&feed_link::WEIGHT_VALID) || std::isfinite(mass);
    }
 public:
    Outbox(const std::string& path,const std::string& review_path,bool requested,bool mock,std::function<size_t(const uint8_t*,size_t)> writer,int64_t now,bool allow_motion=true)
        :writer_(std::move(writer)),source_mock_(mock){
        if(!requested)return;
        if(path.empty() || review_path.empty())throw std::invalid_argument("outbox/review required");
        std::ifstream f(review_path);const std::string body((std::istreambuf_iterator<char>(f)),{});if(body.empty()||body.size()>16384)throw std::invalid_argument("bounded review");
        rejectDuplicateKeys(body);auto owner=own(json_tokener_parse(body.c_str()));auto o=owner.get();
        if(text(o,"scope")!="OWNER_APPROVED_SOLE_OWNER_FEED_LINK" || text(o,"approved_by").empty() || !boolean(o,"maintenance_tx"))throw std::invalid_argument("specific TX review required");
#ifdef FORCAT_BRIDGE_TEST
        if(text(o,"mode")!="MOCK")throw std::invalid_argument("test Bridge cannot promote source to REAL");
#else
        if(text(o,"mode")!="REAL")throw std::invalid_argument("production requires real owner review");
#endif
        expires_=json_object_get_int64(field(o,"valid_until_unix_ms"));if(expires_<=now || expires_-now>86400000)throw std::invalid_argument("expired review");
        producer_=text(o,"producer_id");if(producer_.empty()||producer_.size()>96)throw std::invalid_argument("producer bound");
        review_hash_=text(o,"review_binding");if(review_hash_.size()!=64)throw std::invalid_argument("bound reviewed firmware/evidence digest required");
        review_.sole_owner=true;review_.maintenance_tx=true;
        review_.actuation=boolean(o,"actuation") && allow_motion;review_.servo=boolean(o,"servo_reviewed");review_.power=boolean(o,"power_reviewed");
        review_.calibration=boolean(o,"calibration_reviewed");review_.journal=boolean(o,"journal_reviewed");review_.closure=boolean(o,"closure_reviewed");
        link_.reviewed(review_);
        if(sqlite3_open_v2(path.c_str(),&db_,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_FULLMUTEX,nullptr)!=SQLITE_OK)throw std::runtime_error("outbox DB");
        sqlite3_busy_timeout(db_,80);sql("PRAGMA journal_mode=WAL;");
        sql("CREATE TABLE IF NOT EXISTS cl_transport_tx(seq INTEGER PRIMARY KEY,producer TEXT NOT NULL,packet TEXT NOT NULL,state TEXT NOT NULL,error TEXT);"
            "CREATE TABLE IF NOT EXISTS cl_transport_rx(seq INTEGER PRIMARY KEY,packet TEXT NOT NULL,source TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS cl_wire_consumed(request_id INTEGER PRIMARY KEY,boot INTEGER,origin INTEGER);"
            "CREATE TABLE IF NOT EXISTS cl_transport_state(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL);");
        // CLAIMED/UNCERTAIN rows from a prior owner are never requeued/retransmitted.
        enabled_=true;publish(0);
    }
    ~Outbox(){if(db_)sqlite3_close(db_);}
    bool txAuthorized()const{return enabled_;}
    bool motionAuthorized()const{return enabled_ && link_.motionReady();}
    bool realExecutionPossible()const{return !source_mock_ && motionAuthorized();}
    bool unknownOutcome()const{return link_.unknownOutcome();}
    std::string health(uint32_t now)const{return !connected_?"ESP32_DISCONNECTED":link_.unknownOutcome()?"ESP32_BAD_TELEMETRY":link_.fresh(now)?"ESP32_CONNECTED":"ESP32_STALE";}
    size_t writeOnce(const uint8_t* bytes,size_t size)override{tx_attempted_=true;return connected_?writer_(bytes,size):0;}
    bool consumeReserved(uint32_t id,uint32_t boot,uint32_t origin)override{
        if(!db_ || !requestBound(id,boot,origin))return false;
        try{sql("BEGIN IMMEDIATE");sqlite3_stmt* s=nullptr;bool reserved=false;
            if(sqlite3_prepare_v2(db_,"SELECT source,state,result FROM cl_requests WHERE id=?",-1,&s,nullptr)==SQLITE_OK){
                sqlite3_bind_int64(s,1,id);
                if(sqlite3_step(s)==SQLITE_ROW){const std::string source=reinterpret_cast<const char*>(sqlite3_column_text(s,0)),state=reinterpret_cast<const char*>(sqlite3_column_text(s,1));
                    reserved=source==(source_mock_?"MOCK":"REAL") && (state=="SENT" || state=="PENDING") && !sqlite3_column_text(s,2);}
            }sqlite3_finalize(s);if(!reserved){sql("ROLLBACK");return false;}
            change("INSERT INTO cl_wire_consumed VALUES(?,?,?)",{std::to_string(id),std::to_string(boot),std::to_string(origin)});sql("COMMIT");return true;}
        catch(...){sqlite3_exec(db_,"ROLLBACK",nullptr,nullptr,nullptr);return false;}
    }
    void connection(){connected_=true;link_.disconnect();}
    void disconnect(){connected_=false;link_.disconnect();if(db_)publish(0);}
    unsigned rx(const uint8_t* bytes,size_t size,uint32_t now){
        if(!enabled_)return 0;
        unsigned count=0;
        link_.rx(bytes,size,now,[&](uint32_t id,uint8_t op,const uint8_t* p,uint16_t n){
            if(op==feed_link::RESULT && !resultValid(id,p,n)){error_="INVALID_RESULT_PROOF_OR_REQUEST";return false;}
            uint8_t raw[uart_v1::MAX_FRAME];size_t length=0;
            if(!uart_v1::encode(id,op,p,n,raw,sizeof(raw),length))return false;
            change("INSERT INTO cl_transport_rx(packet,source) VALUES(?,?)",{hex(raw,length),source_mock_?"MOCK":"REAL"});++count;
            return true;
        });return count;
    }
    void pump(uint32_t now,int64_t wall){
        if(!db_)return;
        if(wall>=expires_){enabled_=false;link_.disconnect();error_="OWNER_REVIEW_EXPIRED";publish(now);return;}
        sqlite3_stmt* statement=nullptr;int64_t row=0;std::string producer,packet;
        sql("BEGIN IMMEDIATE");
        if(sqlite3_prepare_v2(db_,"SELECT seq,producer,packet FROM cl_transport_tx WHERE state='QUEUED' ORDER BY seq LIMIT 1",-1,&statement,nullptr)!=SQLITE_OK){sql("ROLLBACK");throw std::runtime_error("queue select");}
        if(sqlite3_step(statement)==SQLITE_ROW){row=sqlite3_column_int64(statement,0);producer=reinterpret_cast<const char*>(sqlite3_column_text(statement,1));packet=reinterpret_cast<const char*>(sqlite3_column_text(statement,2));}
        sqlite3_finalize(statement);
        if(row)change("UPDATE cl_transport_tx SET state='CLAIMED' WHERE seq=? AND state='QUEUED'",{std::to_string(row)});
        sql("COMMIT");
        if(!row){publish(now);return;}
        bool sent=false;tx_attempted_=false;std::string why;
        try{
            if(producer!=producer_)throw std::invalid_argument("unapproved queue producer");
            const auto b=unhex(packet);if(b.size()<12 || b[0]!=0xa5 || b[1]!=0x5a || b[2]!=1 || b.size()!=size_t(feed_link::get16(b.data()+8))+12 ||
                uart_v1::crc16(b.data()+2,b.size()-4)!=feed_link::get16(b.data()+b.size()-2))throw std::invalid_argument("wire CRC/length");
            const auto id=feed_link::get32(b.data()+3);const auto op=b[7];const auto n=feed_link::get16(b.data()+8);const auto p=b.data()+10;
            if(!connected_)throw std::invalid_argument("transport disconnected");
            if(op==feed_link::HELLO){if(n!=5 || p[0]!=1 || feed_link::get32(p+1)!=id)throw std::invalid_argument("HELLO");sent=link_.hello(id,now);}
            else {
                if(n<13 || p[0]!=1 || feed_link::get32(p+1)!=link_.boot() || feed_link::get32(p+5)!=link_.session() || feed_link::get32(p+9)!=link_.nextSequence())throw std::invalid_argument("queued session/sequence mismatch");
                // Link supplies the authoritative increasing sequence; verify the
                // resulting ACK against that same sequence at both ends.
                sent=link_.send(id,op,p+13,static_cast<uint16_t>(n-13),now);
            }
            if(!sent)why="GATES_PEER_FRESHNESS_DUPLICATE_OR_WRITE_FAILURE";
        }catch(const std::exception& e){why=e.what();}
        change("UPDATE cl_transport_tx SET state=?,error=? WHERE seq=?",{sent?"TX_DONE":tx_attempted_?"UNCERTAIN":"BLOCKED",why,std::to_string(row)});
        if(!why.empty())error_=why;publish(now);
    }
    void publish(uint32_t now){
        if(!db_)return;
        auto value=own(json_object_new_object());put(value.get(),"schema","cl_bridge_bound_v1");put(value.get(),"source",source_mock_?"MOCK":"REAL");
        put(value.get(),"connected",connected_);put(value.get(),"tx_reviewed",enabled_);put(value.get(),"motion_ready",motionAuthorized());
        put(value.get(),"unknown_outcome",link_.unknownOutcome());put(value.get(),"error",error_);put(value.get(),"review_binding",review_hash_);
        integer(value.get(),"updated_monotonic_ms",now);integer(value.get(),"boot",link_.boot());integer(value.get(),"session",link_.session());
        change("INSERT OR REPLACE INTO cl_transport_state VALUES(1,?)",{encode(value.get())});
    }
    void fault(const std::string& reason){enabled_=false;error_=reason;link_.disconnect();try{publish(0);}catch(...){} }
};
} // namespace forcat_bind
