#pragma once
// Portable C++14 ROI/configuration/coordinate policy. No camera, GPU or GPIO.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <locale>
#include <map>
#include <sstream>
#include <string>

namespace forcat { namespace food_roi {
enum class Mode {FULL_FRAME,ROI_ENABLED,INVALID};
inline const char* name(Mode m){return m==Mode::FULL_FRAME?"FULL_FRAME":m==Mode::ROI_ENABLED?"ROI_ENABLED":"INVALID";}
inline Mode mode(const std::string& s){return s=="FULL_FRAME"?Mode::FULL_FRAME:s=="ROI_ENABLED"?Mode::ROI_ENABLED:Mode::INVALID;}
struct Box {double x1=0,y1=0,x2=0,y2=0;};
inline bool finiteBox(const Box& b){return std::isfinite(b.x1)&&std::isfinite(b.y1)&&std::isfinite(b.x2)&&std::isfinite(b.y2);}
inline bool validBox(const Box& b){return finiteBox(b)&&b.x1>=0&&b.y1>=0&&b.x1<b.x2&&b.y1<b.y2&&b.x2<=1&&b.y2<=1;}
inline bool validFrame(int w,int h){return w>=2&&h>=2&&w<=16384&&h<=16384;}
struct Config {
 Mode selection=Mode::FULL_FRAME;
 bool syntax_valid=true,coordinates_present=false,calibrated=false;
 Box roi{};
 std::string review_id,camera_device,error;
 int reference_width=0,reference_height=0;
 bool roiReady()const{return syntax_valid&&selection==Mode::ROI_ENABLED&&coordinates_present&&validBox(roi)&&calibrated&&!review_id.empty();}
 bool decisionAllowed()const{return syntax_valid&&(selection==Mode::FULL_FRAME||roiReady());}
 bool compatibleCamera(const std::string& actual)const{return selection==Mode::FULL_FRAME||camera_device.empty()||camera_device==actual;}
};

// Bounded flat JSON configuration reader; shared by offline tests and producer.
// Supports JSON scalars, strict numbers/escapes, rejects duplicate/unknown keys.
namespace detail {
struct Scalar {enum Kind {NULL_VALUE,BOOLEAN,NUMBER,STRING} kind=NULL_VALUE;std::string text;double number=0;bool boolean=false;};
class Reader {
 const std::string& s_;size_t at_=0;
 void ws(){while(at_<s_.size()&&(s_[at_]==' '||s_[at_]=='\r'||s_[at_]=='\n'||s_[at_]=='\t'))++at_;}
 bool take(char c){ws();if(at_>=s_.size()||s_[at_]!=c)return false;++at_;return true;}
 bool hex4(unsigned& value){value=0;for(int i=0;i<4;++i){if(at_>=s_.size())return false;const char c=s_[at_++];
   const int n=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;
   if(n<0)return false;value=(value<<4)|static_cast<unsigned>(n);}return true;}
 static void utf8(std::string& out,unsigned c){
   if(c<0x80)out+=static_cast<char>(c);
   else if(c<0x800){out+=static_cast<char>(0xc0|(c>>6));out+=static_cast<char>(0x80|(c&63));}
   else if(c<0x10000){out+=static_cast<char>(0xe0|(c>>12));out+=static_cast<char>(0x80|((c>>6)&63));out+=static_cast<char>(0x80|(c&63));}
   else{out+=static_cast<char>(0xf0|(c>>18));out+=static_cast<char>(0x80|((c>>12)&63));out+=static_cast<char>(0x80|((c>>6)&63));out+=static_cast<char>(0x80|(c&63));}
 }
 bool text(std::string& out){
   if(!take('"'))return false;
   while(at_<s_.size()){
     unsigned char c=static_cast<unsigned char>(s_[at_++]);if(c=='"')return out.size()<=256;if(c<32)return false;
     if(c!='\\'){out+=static_cast<char>(c);continue;}
     if(at_>=s_.size())return false;const char escape=s_[at_++];
     if(escape=='"'||escape=='\\'||escape=='/')out+=escape;
     else if(escape=='b')out+='\b';else if(escape=='f')out+='\f';else if(escape=='n')out+='\n';else if(escape=='r')out+='\r';else if(escape=='t')out+='\t';
     else if(escape=='u'){
       unsigned code=0;if(!hex4(code))return false;
       if(code>=0xd800&&code<=0xdbff){if(at_+2>s_.size()||s_[at_++]!='\\'||s_[at_++]!='u')return false;unsigned low=0;
         if(!hex4(low)||low<0xdc00||low>0xdfff)return false;code=0x10000+((code-0xd800)<<10)+(low-0xdc00);}
       else if(code>=0xdc00&&code<=0xdfff)return false;
       utf8(out,code);
     }else return false;
   }return false;
 }
 bool scalar(Scalar& v){
   ws();if(at_>=s_.size())return false;
   if(s_[at_]=='"'){v.kind=Scalar::STRING;return text(v.text);}
   for(const auto& token:{std::string("true"),std::string("false"),std::string("null")})if(s_.compare(at_,token.size(),token)==0){
     at_+=token.size();v.kind=token=="null"?Scalar::NULL_VALUE:Scalar::BOOLEAN;v.boolean=token=="true";return true;}
   const size_t start=at_;if(s_[at_]=='-')++at_;
   if(at_>=s_.size()||s_[at_]<'0'||s_[at_]>'9')return false;
   if(s_[at_]=='0')++at_;else while(at_<s_.size()&&s_[at_]>='0'&&s_[at_]<='9')++at_;
   if(at_<s_.size()&&s_[at_]=='.'){++at_;const size_t digit=at_;while(at_<s_.size()&&s_[at_]>='0'&&s_[at_]<='9')++at_;if(digit==at_)return false;}
   if(at_<s_.size()&&(s_[at_]=='e'||s_[at_]=='E')){++at_;if(at_<s_.size()&&(s_[at_]=='+'||s_[at_]=='-'))++at_;const size_t digit=at_;
     while(at_<s_.size()&&s_[at_]>='0'&&s_[at_]<='9')++at_;if(digit==at_)return false;}
   std::istringstream input(s_.substr(start,at_-start));input.imbue(std::locale::classic());input>>v.number;
   if(!input||!input.eof()||!std::isfinite(v.number))return false;v.kind=Scalar::NUMBER;return true;
 }
 public:
 explicit Reader(const std::string& s):s_(s){}
 bool read(std::map<std::string,Scalar>& values){
   if(s_.size()>4096||!take('{'))return false;
   ws();if(at_<s_.size()&&s_[at_]=='}'){++at_;ws();return at_==s_.size();}
   while(at_<s_.size()){
     std::string key;Scalar value;if(!text(key)||!take(':')||!scalar(value)||!values.emplace(key,value).second)return false;
     if(take('}')){ws();return at_==s_.size();}if(!take(','))return false;
   }return false;
 }
};
}
inline Config parseConfig(const std::string& json,Mode override_mode=Mode::INVALID){
 Config c;std::map<std::string,detail::Scalar> v;
 auto invalid=[&](const char* why){c.syntax_valid=false;c.error=why;return c;};
 if(json.size()>4096)return invalid("CONFIG_SIZE_LIMIT");
 if(json.find_first_not_of(" \r\n\t")==std::string::npos){
   if(override_mode!=Mode::INVALID)c.selection=override_mode;
   if(c.selection==Mode::ROI_ENABLED)c.error="ROI_NOT_CALIBRATED_OR_INVALID";
   return c;
 }
 if(!detail::Reader(json).read(v))return invalid("INVALID_CONFIG_JSON");
 for(const auto& p:v)if(p.first!="mode"&&p.first!="enabled"&&p.first!="calibrated"&&p.first!="review_id"&&p.first!="camera_device"&&
   p.first!="width"&&p.first!="height"&&p.first!="x1"&&p.first!="y1"&&p.first!="x2"&&p.first!="y2")return invalid("UNKNOWN_CONFIG_KEY");
 if(v.count("mode")){if(v["mode"].kind!=detail::Scalar::STRING)return invalid("INVALID_MODE_TYPE");c.selection=mode(v["mode"].text);if(c.selection==Mode::INVALID)return invalid("INVALID_MODE");}
 if(v.count("enabled")){
   if(v["enabled"].kind!=detail::Scalar::BOOLEAN)return invalid("INVALID_ENABLED_TYPE");
   const Mode enabled=v["enabled"].boolean?Mode::ROI_ENABLED:Mode::FULL_FRAME;
   c.selection=enabled; // explicit enable/disable wins over a stored mode label
 }
 if(override_mode!=Mode::INVALID)c.selection=override_mode;
 if(v.count("calibrated")){
   if(v["calibrated"].kind!=detail::Scalar::BOOLEAN){if(c.selection==Mode::ROI_ENABLED)return invalid("INVALID_CALIBRATED_TYPE");}
   else c.calibrated=v["calibrated"].boolean;
 }
 for(const auto& key:{"review_id","camera_device"})if(v.count(key)&&v[key].kind!=detail::Scalar::STRING){
   if(c.selection==Mode::ROI_ENABLED)return invalid("INVALID_CONFIG_STRING");v.erase(key);
 }
 c.review_id=v.count("review_id")?v["review_id"].text:"";c.camera_device=v.count("camera_device")?v["camera_device"].text:"";
 double* coordinates[]={&c.roi.x1,&c.roi.y1,&c.roi.x2,&c.roi.y2};const char* keys[]={"x1","y1","x2","y2"};c.coordinates_present=true;
 for(unsigned i=0;i<4;++i){if(!v.count(keys[i])||v[keys[i]].kind!=detail::Scalar::NUMBER)c.coordinates_present=false;else *coordinates[i]=v[keys[i]].number;}
 for(const auto& key:{"width","height"})if(v.count(key)){
   if(v[key].kind!=detail::Scalar::NUMBER||v[key].number<0||v[key].number>16384||std::floor(v[key].number)!=v[key].number){
     if(c.selection==Mode::ROI_ENABLED)return invalid("INVALID_REFERENCE_DIMENSIONS");continue;
   }
   if(std::string(key)=="width")c.reference_width=static_cast<int>(v[key].number);else c.reference_height=static_cast<int>(v[key].number);
 }
 if(c.selection==Mode::ROI_ENABLED&&!c.roiReady())c.error="ROI_NOT_CALIBRATED_OR_INVALID";
 return c;
}

enum class Relation {IN_ROI,OUTSIDE_ROI,FULL_FRAME,INVALID,BLOCKED};
inline const char* name(Relation r){switch(r){case Relation::IN_ROI:return "IN_ROI";case Relation::OUTSIDE_ROI:return "OUTSIDE_ROI";case Relation::FULL_FRAME:return "NOT_EVALUATED_FULL_FRAME";case Relation::INVALID:return "INVALID";default:return "BLOCKED";}}
inline Relation evaluate(const Config& c,const Box& box,int width,int height){
 if(!validFrame(width,height)||!validBox(box))return Relation::INVALID;
 if(!c.decisionAllowed())return Relation::BLOCKED;
 if(c.selection==Mode::FULL_FRAME)return Relation::FULL_FRAME;
 const double cx=(box.x1+box.x2)/2,cy=(box.y1+box.y2)/2;
 const double overlap=std::max(0.0,std::min(box.x2,c.roi.x2)-std::max(box.x1,c.roi.x1))*
                      std::max(0.0,std::min(box.y2,c.roi.y2)-std::max(box.y1,c.roi.y1));
 const double area=(box.x2-box.x1)*(box.y2-box.y1);
 return cx>c.roi.x1&&cx<c.roi.x2&&cy>c.roi.y1&&cy<c.roi.y2&&overlap/area>=0.5?Relation::IN_ROI:Relation::OUTSIDE_ROI;
}
struct ConvertedBox {bool valid=false;Box box{};};
inline ConvertedBox originalPixels(const Box& b,int w,int h){
 if(!validFrame(w,h)||!finiteBox(b)||b.x1<0||b.y1<0||b.x1>=b.x2||b.y1>=b.y2||b.x2>w||b.y2>h)return {};
 return {true,{b.x1/w,b.y1/h,b.x2/w,b.y2/h}};
}
struct Letterbox {bool valid=false;float scale=0;int pad_x=0,pad_y=0;};
inline Letterbox letterbox(int w,int h,int net_w=320,int net_h=320){
 if(!validFrame(w,h)||!validFrame(net_w,net_h))return {};
 const float scale=std::min(static_cast<float>(net_w)/w,static_cast<float>(net_h)/h);
 const int resized_w=static_cast<int>(std::round(w*scale)),resized_h=static_cast<int>(std::round(h*scale));
 if(resized_w<1||resized_h<1)return {};
 return {true,scale,(net_w-resized_w)/2,(net_h-resized_h)/2};
}
// ONLY for raw network-pixel boxes. Existing Detector::infer() already returns
// normalized ORIGINAL-frame boxes: evaluate those directly, never undo twice.
inline ConvertedBox letterboxedPixels(const Box& b,int w,int h,int net_w=320,int net_h=320){
 const auto t=letterbox(w,h,net_w,net_h);
 if(!t.valid||!finiteBox(b)||b.x1<0||b.y1<0||b.x2>net_w||b.y2>net_h||b.x1>=b.x2||b.y1>=b.y2)return {};
 const auto clamp=[](float x,int maximum){return std::max(0.0f,std::min(x,static_cast<float>(maximum-1)));};
 const float x1=clamp((static_cast<float>(b.x1)-t.pad_x)/t.scale,w),x2=clamp((static_cast<float>(b.x2)-t.pad_x)/t.scale,w);
 const float y1=clamp((static_cast<float>(b.y1)-t.pad_y)/t.scale,h),y2=clamp((static_cast<float>(b.y2)-t.pad_y)/t.scale,h);
 const int x=static_cast<int>(x1),y=static_cast<int>(y1),bw=static_cast<int>(x2-x1),bh=static_cast<int>(y2-y1);
 if(bw<=1||bh<=1)return {};
 return originalPixels({static_cast<double>(x),static_cast<double>(y),static_cast<double>(x+bw),static_cast<double>(y+bh)},w,h);
}
inline bool evidenceAllowed(Mode expected,Mode advertised,bool config_valid,bool calibrated,bool bbox_available,bool decision_eligible){
 if(expected==Mode::INVALID||advertised!=expected||!config_valid||!decision_eligible)return false;
 return expected==Mode::FULL_FRAME||(calibrated&&bbox_available);
}
} } // namespace forcat::food_roi
