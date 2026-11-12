// Intentionally faulty runtime probes ONLY. Never part of product firmware.
#include <climits>
#include <string>
int main(int argc,char** argv) {
  if (argc==2 && std::string(argv[1])=="asan") {
    volatile int* data=new int[1]; volatile int index=2;
    data[index]=7; const int value=data[index]; delete[] data; return value;
  }
  volatile int maximum=INT_MAX,one=1;
  volatile int overflow=maximum+one; return overflow;
}
