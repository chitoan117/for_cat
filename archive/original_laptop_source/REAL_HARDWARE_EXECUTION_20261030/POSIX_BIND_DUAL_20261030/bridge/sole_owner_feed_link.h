#pragma once
// Injection point for the CURRENT C++ Bridge's already-owned fd. This library
// never opens a tty, changes systemd, takes ownership, or grants its own approval.
#include "feed_link.h"
#include "dog_warning_protocol.h"
#include <set>
#include <string>
namespace forcat_feed_bridge {
class Writer {
 public:virtual ~Writer()=default;
    virtual size_t writeOnce(const uint8_t* bytes,size_t size)=0;
};
class DurableStore {
 public:virtual ~DurableStore()=default;
    // Must atomically consume a previously reserved request before any write.
    virtual bool consumeReserved(uint32_t request_id,uint32_t boot,uint32_t session)=0;
};
struct Review {
    bool sole_owner=false,maintenance_tx=false,actuation=false,servo=false,power=false,calibration=false,journal=false,closure=false;
    bool motion()const{return sole_owner&&maintenance_tx&&actuation&&servo&&power&&calibration&&journal&&closure;}
};
class Link {
    Writer& writer_;DurableStore& store_;Review review_;
    dog_wire::Parser parser_;
    uint32_t expected_hello_=0,boot_=0,session_=0,sequence_=0,last_rx_=0;
    uint8_t flags_=0,last_operation_=0;uint32_t last_id_=0;bool peer_=false,unknown_=false;
    uint32_t max_rx_sequence_=0;std::set<std::string> rx_at_sequence_;
    bool write(uint32_t id,uint8_t op,const uint8_t* payload,uint16_t n){
        uint8_t bytes[uart_v1::MAX_FRAME]{};size_t size=0;
        if(!uart_v1::encode(id,op,payload,n,bytes,sizeof(bytes),size))return false;
        const bool ok=writer_.writeOnce(bytes,size)==size;
        if(!ok){unknown_=true;peer_=false;} // partial write is never retried automatically
        return ok;
    }
 public:
    Link(Writer& writer,DurableStore& store):writer_(writer),store_(store){}
    void reviewed(Review value){review_=value;}
    bool unknownOutcome()const{return unknown_;}
    bool connected()const{return peer_;}
    bool fresh(uint32_t now)const{return peer_ && now-last_rx_<=1500;}
    bool motionReady()const{return peer_ && review_.motion() && (flags_&7u)==7u;}
    uint32_t boot()const{return boot_;}
    uint32_t session()const{return session_;}
    uint32_t nextSequence()const{return sequence_==UINT32_MAX?0:sequence_+1;}
    void disconnect(){peer_=false;expected_hello_=0;parser_.reset();rx_at_sequence_.clear();max_rx_sequence_=0;}
    bool hello(uint32_t nonce,uint32_t now){
        if(!review_.sole_owner || !review_.maintenance_tx || !nonce || unknown_)return false;
        expected_hello_=nonce;peer_=false;sequence_=0;last_rx_=now;
        uint8_t p[5]{1};feed_link::put32(p+1,nonce);return write(nonce,feed_link::HELLO,p,5);
    }
    template<class F> void rx(const uint8_t* bytes,size_t size,uint32_t now,F accepted){
        for(size_t i=0;i<size;++i)parser_.feed(bytes[i],now,[&](uint32_t id,uint8_t op,const uint8_t* p,uint16_t n){
            if(op==feed_link::CAPABILITIES){
                if(n!=23 || p[0]!=1 || !expected_hello_ || id!=expected_hello_ || !feed_link::get32(p+1) || !feed_link::get32(p+5) || (p[13]&~15u) || p[18]>1 || p[19]>9)return;
                boot_=feed_link::get32(p+1);session_=feed_link::get32(p+5);flags_=p[13];expected_hello_=0;peer_=true;max_rx_sequence_=0;rx_at_sequence_.clear();
            }else{
                if(!peer_ || n<13 || p[0]!=1 || feed_link::get32(p+1)!=boot_ || feed_link::get32(p+5)!=session_ || feed_link::get32(p+9)>sequence_)return;
                if((op==uart_v1::ACK || op==uart_v1::NACK) && (n!=15 || feed_link::get32(p+9)!=sequence_ || p[13]!=last_operation_ || id!=last_id_))return;
                if(op==uart_v1::ACK && n==15 && p[14]==0 && last_operation_==feed_link::CONFIGURE)flags_|=8;
                if(op!=uart_v1::ACK && op!=uart_v1::NACK && op!=feed_link::RESULT)return;
            }
            const auto seq=feed_link::get32(p+9);
            if(seq<max_rx_sequence_)return;
            std::string signature(reinterpret_cast<const char*>(p),n);signature+=static_cast<char>(op);
            for(unsigned i=0;i<4;++i)signature+=static_cast<char>(id>>(i*8));
            if(seq>max_rx_sequence_)rx_at_sequence_.clear();
            if(rx_at_sequence_.count(signature) || rx_at_sequence_.size()>=8)return;
            if(accepted(id,op,p,n)){max_rx_sequence_=seq;rx_at_sequence_.insert(signature);last_rx_=now;}
        });
    }
    bool send(uint32_t id,uint8_t op,const uint8_t* tail,uint16_t length,uint32_t now){
        if(!peer_ || unknown_ || !review_.sole_owner || !review_.maintenance_tx || now-last_rx_>1500 || length>35 || (length && !tail) || sequence_==UINT32_MAX)return false;
        const bool motion=op==feed_link::CONFIGURE || op==feed_link::ARM || op==feed_link::FEED || op==feed_link::DOG || op==feed_link::INSPECT;
        if(motion && (!review_.motion() || (flags_&7u)!=7u))return false;
        if(op!=feed_link::CONFIGURE && op!=feed_link::ARM && op!=feed_link::FEED && op!=feed_link::HEARTBEAT &&
           op!=feed_link::ABORT && op!=feed_link::QUERY && op!=feed_link::DOG && op!=feed_link::INSPECT)return false;
        if((op==feed_link::CONFIGURE && length!=35) || (op!=feed_link::CONFIGURE && length!=0))return false;
        if(op==feed_link::FEED && (!(flags_&8u) || !id || id>0xffffffu || !store_.consumeReserved(id,boot_,session_)))return false;
        uint8_t p[48]{1};feed_link::put32(p+1,boot_);feed_link::put32(p+5,session_);feed_link::put32(p+9,++sequence_);
        if(length)std::memcpy(p+13,tail,length);last_operation_=op;last_id_=id;
        return write(id,op,p,static_cast<uint16_t>(13+length));
    }
};
} // namespace forcat_feed_bridge
