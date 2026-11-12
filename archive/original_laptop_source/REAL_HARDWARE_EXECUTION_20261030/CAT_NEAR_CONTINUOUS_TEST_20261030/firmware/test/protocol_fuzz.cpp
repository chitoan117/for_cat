#define FIRMWARE_BRIDGE_NO_MAIN 1
#include "firmware_bridge.cpp"

int main(int argc,char** argv) {
  try {
    const unsigned iterations=argc>1?static_cast<unsigned>(std::stoul(argv[1])):2000;
    bridge::need(iterations>0 && iterations<=10000,"fuzz budget");
    std::uint32_t random=0xc0ffeeu; unsigned checks=0;
    const auto check=[&](bool ok) { ++checks; bridge::need(ok,"protocol fuzz invariant"); };
    const auto next=[&]() { random^=random<<13; random^=random>>17; random^=random<<5; return random; };
    const auto frame=[](std::uint32_t id,std::uint8_t command) {
      std::uint8_t data[uart_v1::MAX_FRAME]; std::size_t n=0;
      bridge::need(uart_v1::encode(id,command,nullptr,0,data,sizeof(data),n),"fuzz encode");
      return std::string(reinterpret_cast<char*>(data),n);
    };
    setup(); Serial0.tx.clear();
    for (unsigned i=0;i<iterations;++i) {
      std::string noise; const auto n=next()%512u;
      for (unsigned j=0;j<n;++j) noise+=static_cast<char>(next()&255u);
      Serial0.input(noise); bridge::tick(0); bridge::tick(251); Serial0.tx.clear();
      auto bad=frame(100000+i,uart_v1::FEED_REQUEST); bad.back()^=static_cast<char>(1u<<(next()%8u));
      const auto cut=1u+next()%static_cast<unsigned>(bad.size());
      Serial0.input(bad.substr(0,cut)); bridge::tick(0); Serial0.input(bad.substr(cut)); bridge::tick(0);
      bridge::tick(251); Serial0.tx.clear();
      Serial0.input(frame(100000+i,uart_v1::FEED_STATUS)+frame(200000+i,uart_v1::PING)); bridge::tick(0);
      const auto& out=Serial0.tx;
      check(out.size()==26);
      check(static_cast<unsigned char>(out[7])==uart_v1::NACK && static_cast<unsigned char>(out[10])==5);
      check(static_cast<unsigned char>(out[20])==uart_v1::ACK && static_cast<unsigned char>(out[23])==uart_v1::PING);
      check(uart_v1::crc16(reinterpret_cast<const std::uint8_t*>(out.data()+2),9)==
          (static_cast<unsigned char>(out[11]) | static_cast<unsigned>(static_cast<unsigned char>(out[12]))<<8));
      check(used==0 && !controller.feed.openRequested() && !controller.water.pumpRequested());
      check(host_board::nvs_writes==0 && host_board::touches[14]==0 && host_board::touches[15]==0);
      Serial0.tx.clear();
    }
    std::cout<<"{\"named_cases\":1,\"seed\":12648430,\"iterations\":"<<iterations
             <<",\"assertions\":"<<checks<<",\"scope\":\"SOFTWARE_ONLY\",\"result\":\"PASS\"}\n";
    return 0;
  } catch (const std::exception& error) { std::cerr<<error.what()<<'\n'; return 1; }
}
