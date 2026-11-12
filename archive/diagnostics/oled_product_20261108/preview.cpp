#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <assert.h>
#include <stdlib.h>
#undef isfinite
namespace std {
using ::snprintf;using ::strcmp;using ::strcpy;using ::strlen;using ::memset;
using ::fopen;using ::fprintf;using ::fclose;using ::printf;using ::abs;
inline bool isfinite(float x){return __builtin_isfinite(x);}
inline float fabs(float x){return __builtin_fabsf(x);}
}
#include "C:/Arduino/libraries/Adafruit_GFX_Library/glcdfont.c"
#define SSD1306_WHITE 1
#define SSD1306_BLACK 0

namespace bench_v8 {
enum class FeedStage : uint8_t {IDLE,WAIT_HX,WAIT_CAT,OPENING,WAIT_WEIGHT,CLOSING,DIAG_OPEN,DIAG_CLOSE,DONE,FAULT};
constexpr float CLOSE_AT_G=35.0f;
}
struct MockDisplay {
  uint8_t pixels[64][128]{};
  int cx=0,cy=0,scale=1,color=1;
  void clearDisplay(){std::memset(pixels,0,sizeof(pixels));}
  void setFont(const void*){}
  void setTextWrap(bool wrap){assert(!wrap);}
  void setTextSize(int value){scale=value;}
  void setTextColor(int value){color=value;}
  void setCursor(int x,int y){cx=x;cy=y;}
  void display(){}
  void drawPixel(int x,int y,int c){assert(x>=0&&x<128&&y>=0&&y<64);pixels[y][x]=c;}
  void fillRect(int x,int y,int w,int h,int c){for(int j=y;j<y+h;++j)for(int i=x;i<x+w;++i)drawPixel(i,j,c);}
  void drawFastHLine(int x,int y,int w,int c){fillRect(x,y,w,1,c);}
  void drawFastVLine(int x,int y,int h,int c){fillRect(x,y,1,h,c);}
  void fillCircle(int x,int y,int r,int c){for(int j=-r;j<=r;++j)for(int i=-r;i<=r;++i)if(i*i+j*j<=r*r)drawPixel(x+i,y+j,c);}
  bool inRound(int x,int y,int w,int h,int r,int i,int j){
    int a=i,b=j;
    if(a<x+r)a=x+r;else if(a>x+w-r-1)a=x+w-r-1;
    if(b<y+r)b=y+r;else if(b>y+h-r-1)b=y+h-r-1;
    return (a-i)*(a-i)+(b-j)*(b-j)<=r*r;
  }
  void fillRoundRect(int x,int y,int w,int h,int r,int c){for(int j=y;j<y+h;++j)for(int i=x;i<x+w;++i)if(inRound(x,y,w,h,r,i,j))drawPixel(i,j,c);}
  void drawRoundRect(int x,int y,int w,int h,int r,int c){for(int j=y;j<y+h;++j)for(int i=x;i<x+w;++i){
    bool inner=i>x&&i<x+w-1&&j>y&&j<y+h-1&&inRound(x+1,y+1,w-2,h-2,r-1,i,j);
    if(inRound(x,y,w,h,r,i,j)&&!inner)drawPixel(i,j,c);
  }}
  void line(int x,int y,int xx,int yy,int c){
    int dx=std::abs(xx-x),sx=x<xx?1:-1,dy=-std::abs(yy-y),sy=y<yy?1:-1,e=dx+dy;
    while(true){drawPixel(x,y,c);if(x==xx&&y==yy)break;int n=2*e;if(n>=dy){e+=dy;x+=sx;}if(n<=dx){e+=dx;y+=sy;}}
  }
  void drawTriangle(int x,int y,int a,int b,int q,int z,int c){line(x,y,a,b,c);line(a,b,q,z,c);line(q,z,x,y,c);}
  void print(const char* value){
    assert(cx>=0&&cy>=0&&cy+8*scale<=64&&cx+int(std::strlen(value))*6*scale<=128);
    for(const unsigned char* p=(const unsigned char*)value;*p;++p){
      for(int i=0;i<5;++i)for(int j=0;j<8;++j)if(font[*p*5+i]&(1<<j))fillRect(cx+i*scale,cy+j*scale,scale,scale,color);
      cx+=6*scale;
    }
  }
  void save(const char* name){FILE* f=std::fopen(name,"w");assert(f);std::fprintf(f,"P2\n128 64\n255\n");for(auto& row:pixels){for(auto p:row)std::fprintf(f,"%d ",p?255:0);std::fprintf(f,"\n");}std::fclose(f);}
} oled;

#include "render.inc"

int main(){
  using namespace product_oled;
  using Stage=bench_v8::FeedStage;
  View v{};v.ai="FAIL";v.scale_ok=true;v.grams=2;v.delta=NAN;v.stage=Stage::IDLE;
  v.cm[0]=71;v.cm[1]=13.6;v.cm[2]=56.7;v.cm[3]=19.6;
  const char* labels[]={"FAIL","CAT","DOG"};
  const float weights[]={-99999,-2,0,2,35,999.9f,1000,99999,100000,NAN};
  unsigned cases=0;
  const uint32_t times[]={1000u,9500u,0xfffffffeu};
  for(int stage=0;stage<10;++stage)for(auto ai:labels)for(float grams:weights){
    v.stage=static_cast<Stage>(stage);v.ai=ai;v.grams=grams;
    for(uint32_t now: times) {render(v,now);++cases;}
  }
  v.ai="FAIL";v.grams=2;v.stage=Stage::IDLE;
  assert(showDetails(v,9500));v.stage=Stage::WAIT_WEIGHT;assert(!showDetails(v,9500));
  v.stage=Stage::IDLE;v.ai="CAT";assert(!showDetails(v,9500));v.ai="FAIL";
  v.inspect=true;assert(!showDetails(v,9500));v.inspect=false;
  v.paused=true;assert(!showDetails(v,9500));v.paused=false;
  bool warning=false;assert(!std::strcmp(status(v,warning),"SAN SANG"));
  v.stage=Stage::FAULT;v.delta=18.9f;assert(!std::strcmp(status(v,warning),"LAN CAP CHUA DU")&&warning);
  v.stage=Stage::IDLE;render(v,1000);oled.save("home.pgm");
  v.ai="CAT";render(v,1000);oled.save("cat.pgm");
  v.ai="DOG";v.dog=true;render(v,1000);oled.save("dog.pgm");v.dog=false;
  v.ai="FAIL";v.stage=Stage::WAIT_WEIGHT;v.grams=23.7;v.delta=23.7;render(v,1000);oled.save("feeding.pgm");
  v.stage=Stage::CLOSING;v.grams=35;v.delta=35;render(v,1000);oled.save("closing.pgm");
  v.stage=Stage::FAULT;v.grams=18.9;v.delta=18.9;render(v,1000);oled.save("warning.pgm");
  v.stage=Stage::IDLE;render(v,9500);oled.save("sensors.pgm");
  v.scale_ok=false;render(v,9500);oled.save("no_scale.pgm");
  v.scale_ok=true;v.inspect=true;render(v,1000);oled.save("inspection.pgm");
  v.inspect=false;v.paused=true;render(v,1000);oled.save("paused.pgm");
  v.paused=false;v.calibrating=true;render(v,1000);oled.save("calibration.pgm");
  boot();oled.save("boot.pgm");
  std::printf("PASS: %u layout frames, all phases/AI/numeric extremes/rollover within128x64; page priority, honest underdose and missing-scale status.\n",cases);
}
