from pathlib import Path
import subprocess,os
r=Path(__file__).parent
s=(r/'esp32/esp32.ino').read_text(encoding='utf-8')
uno=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\CODE_TEST_LOADCELL_CHUAN.ino').read_text(encoding='utf-8')
def block(text,marker):
 a=text.index(marker);b=text.index('{',a);e=b+1;n=1
 while n:
  if text[e]=='{':n+=1
  if text[e]=='}':n-=1
  e+=1
 return text[a:e]
h='''#include <assert.h>
#include <stdint.h>
#include <math.h>
#include <stdio.h>
#undef isfinite
namespace std { inline bool isfinite(double x){return __builtin_isfinite(x);} inline double fabs(double x){return __builtin_fabs(x);} }
template<class T> struct Reading { bool valid;T value;uint32_t sampled_at_ms;bool fresh; };
bool rawValid(double raw){return std::isfinite(raw)&&raw>=-8388608&&raw<=8388607;}
struct ScaleCalibration {double tare_counts=-668483,grams_per_count=1.0/-1064.4473;bool valid()const{return true;}};
'''
h+=block(s,'class Hx711Median3 {')+';\n'
h+=block(s,'inline Reading<float> hx711SignedGrams(')+'\n'
h+=block(s,'class Hx711ReferenceDisplay {')+';\n'
h+=block(uno,'long median3(')+'\n'
a=uno.index('  if (currentWeight > -ZERO_DEADBAND')
b=uno.index('  // HIEN THI',a)
body=uno[a:b]
# Last comment separator is harmless; constants are read from actual reference source.
h+='float unoDisplay(float currentWeight,float& displayedWeight){\n'
for line in uno.splitlines():
 if line.startswith('const float '):h+=line+'\n'
h+=body+'\nreturn displayedWeight;\n}\n'
h+='''int main(){
 Hx711Median3 m;int32_t out=0;
 for(int a=-2;a<=2;a++)for(int b=-2;b<=2;b++)for(int c=-2;c<=2;c++){
   m.reset();assert(!m.add(a,out));assert(!m.add(b,out));assert(m.add(c,out));assert(out==median3(a,b,c));
 }
 ScaleCalibration cal;Hx711ReferenceDisplay d;float golden=0;
 float weights[]={0,0.19f,-0.19f,-0.49f,-0.51f,0.5f,0.8f,1.8f,38,38.2f,37.9f,20,0,-2,999,0};
 for(int repetition=0;repetition<100;repetition++)for(float g:weights){
   int32_t raw=(int32_t)(-668483.0+g*-1064.4473);
   float expected=((float)(raw-(-668483)))/-1064.4473f;
   auto measured=hx711SignedGrams(cal,raw,123);
   assert(measured.valid&&__builtin_fabsf(measured.value-expected)<0.001f);
   auto actual=d.update(measured);
   assert(actual.valid&&__builtin_fabsf(actual.value-unoDisplay(expected,golden))<0.002f);
 }
 assert(!d.update({false,0,0,true}).valid);
 assert(!d.update({true,NAN,0,true}).valid);
 assert(!d.update({true,10,0,false}).valid);
 puts("PASS: all median3 permutations;1600 signed conversion/display comparisons against actual UNO source; invalid/nonfresh sample rejection");
}
'''
(r/'uno_reference_test.cpp').write_text(h,encoding='utf-8')
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(r.parent/'timed_close_20261103/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(r/'zig-local-cache')
subprocess.run([r'D:\Agent_Cat\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe','c++','-std=c++17','-nostdlib++','-fno-exceptions','-fno-rtti',str(r/'uno_reference_test.cpp'),'-o',str(r/'uno_reference_test.exe')],check=True,env=env)
p=subprocess.run([str(r/'uno_reference_test.exe')],capture_output=True,text=True,check=True)
(r/'uno_reference_test_result.txt').write_text(p.stdout);print(p.stdout)
