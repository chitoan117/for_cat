// C++14, portable, synthetic inputs only. No serial/camera/database/actuator API.
#include "food_roi.h"
#include "roi_species.h"
#include "approach_fusion.h"
#include "feed_policy.h"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace roi=forcat::food_roi;
namespace {
unsigned checks=0,groups=0;
#define CHECK(value) do { ++checks; if(!(value)) throw std::runtime_error("check line="+std::to_string(__LINE__)); } while(false)
template<class F> void test(const char* label,F body){
    body();++groups;std::cout<<"PASS "<<label<<'\n';
}
const std::string ready="\"enabled\":true,\"calibrated\":true,\"review_id\":\"TEST_ONLY\",\"x1\":0.25,\"y1\":0.25,\"x2\":0.75,\"y2\":0.75";
std::string hex(const std::string& value){
    const char* digits="0123456789abcdef";std::string out;
    for(unsigned char c:value){out+=digits[c>>4];out+=digits[c&15];}
    return out;
}
int nibble(char c){return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;}
std::string unhex(const std::string& value){
    if(value.size()%2)throw std::invalid_argument("hex length");
    std::string out;
    for(size_t i=0;i<value.size();i+=2){
        int a=nibble(value[i]),b=nibble(value[i+1]);
        if(a<0||b<0)throw std::invalid_argument("hex character");
        out+=static_cast<char>((a<<4)|b);
    }
    return out;
}
// Stable observation of public config + flat-reader scalars. The Windows runner
// compares baseline and candidate for exactly the same byte inputs and overrides.
int probe(){
    std::cout.imbue(std::locale::classic());std::cout<<std::setprecision(17);
    std::string line;
    while(std::getline(std::cin,line)){
        if(line.size()<2||line[1]!=':'||line[0]<'0'||line[0]>'2')return 2;
        const std::string input=unhex(line.substr(2));
        const auto override_mode=line[0]=='0'?roi::Mode::INVALID:line[0]=='1'?roi::Mode::FULL_FRAME:roi::Mode::ROI_ENABLED;
        const auto c=roi::parseConfig(input,override_mode);
        std::map<std::string,roi::detail::Scalar> scalars;
        const bool parsed=roi::detail::Reader(input).read(scalars);
        std::cout<<c.syntax_valid<<'|'<<roi::name(c.selection)<<'|'<<c.coordinates_present<<'|'<<c.calibrated
                 <<'|'<<hex(c.review_id)<<'|'<<hex(c.camera_device)<<'|'<<hex(c.error)
                 <<'|'<<c.reference_width<<'|'<<c.reference_height<<'|'<<c.roi.x1<<'|'<<c.roi.y1
                 <<'|'<<c.roi.x2<<'|'<<c.roi.y2<<'|'<<c.roiReady()<<'|'<<c.decisionAllowed()
                 <<'|'<<c.compatibleCamera("TEST_CAMERA")<<'|'<<parsed<<'|'<<scalars.size();
        for(const auto& entry:scalars){
            const auto& s=entry.second;
            std::cout<<'|'<<hex(entry.first)<<':'<<static_cast<int>(s.kind)<<':'<<hex(s.text)<<':'<<s.number<<':'<<s.boolean;
        }
        std::cout<<'\n';
    }
    return 0;
}
void suite(){
    test("unicode_BMP_NUL_and_raw_UTF8",[]{
        CHECK(roi::parseConfig("{\"review_id\":\"\\u0041\\u00e9\\u20ac\"}").review_id=="A\xc3\xa9\xe2\x82\xac");
        CHECK(roi::parseConfig("{\"review_id\":\"a\\u0000b\"}").review_id==std::string("a\0b",3));
        CHECK(roi::parseConfig("{\"review_id\":\"\xc3\xa9\"}").review_id=="\xc3\xa9");
        CHECK(roi::parseConfig("{\"review_id\":\"\\\"\\\\\\/\\b\\f\\n\\r\\t\"}").review_id==std::string("\"\\/\b\f\n\r\t"));
    });
    test("UTF16_surrogate_pairs_and_limits",[]{
        CHECK(roi::parseConfig("{\"review_id\":\"\\uD83D\\uDE00\"}").review_id=="\xf0\x9f\x98\x80");
        CHECK(roi::parseConfig("{\"review_id\":\"\\uD800\\uDC00\"}").review_id=="\xf0\x90\x80\x80");
        CHECK(roi::parseConfig("{\"review_id\":\"\\uDBFF\\uDFFF\"}").review_id=="\xf4\x8f\xbf\xbf");
        for(const char* text:{"\\ud800","\\udfff","\\ud800\\u0041","\\ud800x","\\ud800\\ud800","\\ud800\\uDC0","\\u12g4","\\u123","\\U0041"}){
            CHECK(!roi::parseConfig(std::string("{\"review_id\":\"")+text+"\"}").syntax_valid);
        }
    });
    test("duplicate_and_escaped_keys",[]{
        for(const char* text:{"{\"enabled\":false,\"enabled\":true}","{\"enabled\":false,\"enabl\\u0065d\":true}","{\"review_id\":\"A\",\"r\\u0065view_id\":\"B\"}"}){
            CHECK(!roi::parseConfig(text).syntax_valid);
        }
        CHECK(roi::parseConfig("{\"enabl\\u0065d\":false}").decisionAllowed());
        CHECK(roi::parseConfig("{\"unknown\":1}").error=="UNKNOWN_CONFIG_KEY");
    });
    test("malformed_JSON_and_trailing_bytes",[]{
        for(const char* text:{"{","[]","null","true","{\"enabled\":true,}","{\"enabled\" true}","{\"enabled\":true}{}","{} trailing","{\"review_id\":\"\\q\"}","{\"review_id\":\"unterminated}","{\"review_id\":[]}","{\"review_id\":{}}","{\"x1\":True}"}){
            CHECK(!roi::parseConfig(text).syntax_valid);
        }
        CHECK(!roi::parseConfig(std::string("{\"review_id\":\"a\nb\"}")).syntax_valid);
        CHECK(!roi::parseConfig(std::string("{}\0",3)).syntax_valid);
    });
    test("strict_numeric_parsing",[]{
        for(const char* number:{"0","-0","0.25","1e2","-1.5E-2","1E+0"}){
            CHECK(roi::parseConfig(std::string("{\"x1\":")+number+"}").syntax_valid);
        }
        CHECK(roi::parseConfig("{\"x1\":1e-1}").roi.x1==0.1);
        for(const char* number:{"+1","01","-01",".1","1.","1e","1e+","--1","NaN","Infinity","1e309","0x1"}){
            CHECK(!roi::parseConfig(std::string("{\"x1\":")+number+"}").syntax_valid);
        }
    });
    test("byte_and_config_size_boundaries",[]{
        CHECK(roi::parseConfig("{}"+std::string(4094,' ')).syntax_valid);
        CHECK(!roi::parseConfig("{}"+std::string(4095,' ')).syntax_valid);
        CHECK(roi::parseConfig(std::string(4096,' ')).decisionAllowed());
        CHECK(!roi::parseConfig(std::string(4097,' ')).syntax_valid);
        CHECK(roi::parseConfig("{\"review_id\":\""+std::string(256,'a')+"\"}").syntax_valid);
        CHECK(!roi::parseConfig("{\"review_id\":\""+std::string(257,'a')+"\"}").syntax_valid);
    });
    test("mode_enabled_override_and_metadata_types",[]{
        CHECK(roi::parseConfig("{}").decisionAllowed());
        CHECK(!roi::parseConfig("{}",roi::Mode::ROI_ENABLED).decisionAllowed());
        CHECK(roi::parseConfig("{\"mode\":\"ROI_ENABLED\",\"enabled\":false}").decisionAllowed());
        CHECK(roi::parseConfig("{"+ready+"}",roi::Mode::FULL_FRAME).selection==roi::Mode::FULL_FRAME);
        for(const char* text:{"{\"enabled\":1}","{\"mode\":true}","{\"mode\":\"BAD\"}","{\"enabled\":true,\"calibrated\":1}","{\"enabled\":true,\"review_id\":null}","{\"enabled\":true,\"camera_device\":12}"}){
            CHECK(!roi::parseConfig(text).syntax_valid);
        }
        auto c=roi::parseConfig("{\"enabled\":false,\"calibrated\":\"bad\",\"review_id\":null,\"camera_device\":12,\"width\":-1,\"height\":1.5}");
        CHECK(c.syntax_valid&&c.decisionAllowed()&&c.review_id.empty()&&c.camera_device.empty());
        CHECK(c.reference_width==0&&c.reference_height==0);
    });
    test("ROI_validation_and_reference_dimensions",[]{
        const auto c=roi::parseConfig("{"+ready+",\"width\":640,\"height\":480}");
        CHECK(c.roiReady()&&c.decisionAllowed()&&c.reference_width==640&&c.reference_height==480);
        for(const char* value:{"-1","1.5","16385","null","\"640\""}){
            CHECK(!roi::parseConfig("{"+ready+",\"width\":"+value+"}").syntax_valid);
            CHECK(roi::parseConfig(std::string("{\"enabled\":false,\"width\":")+value+"}").decisionAllowed());
        }
        for(const auto b:{roi::Box{-.1,.2,.8,.8},roi::Box{.2,.2,1.1,.8},roi::Box{.5,.2,.5,.8},roi::Box{.6,.2,.5,.8}}){
            auto invalid=c;invalid.roi=b;CHECK(!invalid.roiReady()&&!invalid.decisionAllowed());
        }
        CHECK(!roi::parseConfig("{\"enabled\":true,\"calibrated\":true,\"review_id\":\"TEST_ONLY\"}").roiReady());
    });
    test("geometry_and_classification_scope",[]{
        auto c=roi::parseConfig("{"+ready+"}");
        CHECK(roi::evaluate(c,{.35,.35,.65,.65},640,480)==roi::Relation::IN_ROI);
        CHECK(roi::evaluate(c,{.02,.02,.18,.18},640,480)==roi::Relation::OUTSIDE_ROI);
        CHECK(roi::evaluate(c,{.1,.35,.25,.65},640,480)==roi::Relation::OUTSIDE_ROI);
        CHECK(roi::evaluate(c,{0,0,1,1},640,480)==roi::Relation::OUTSIDE_ROI);
        CHECK(roi::evaluate(c,{.35,.35,.65,.65},0,480)==roi::Relation::INVALID);
        forcat::RoiSpecies scene(c,640,480);
        scene.box(false,true,.9,.35,.35,.65,.65);CHECK(scene.species()=="CAT");
        scene.box(true,false,.9,.35,.35,.65,.65);CHECK(scene.species()=="DOG");
        CHECK(!roi::evidenceAllowed(roi::Mode::ROI_ENABLED,roi::Mode::FULL_FRAME,true,false,false,true));
        CHECK(!roi::evidenceAllowed(roi::Mode::ROI_ENABLED,roi::Mode::ROI_ENABLED,true,true,false,true));
        CHECK(roi::evidenceAllowed(roi::Mode::FULL_FRAME,roi::Mode::FULL_FRAME,true,false,false,true));
        CHECK(forcat::FEED_TARGET_GRAMS==35&&forcat::WaterDryRun::actuator_execution==false);
    });
    test("coordinate_conversion_and_camera_binding",[]{
        auto c=roi::parseConfig("{"+ready+",\"camera_device\":\"TEST_CAMERA\"}");
        CHECK(c.compatibleCamera("TEST_CAMERA")&&!c.compatibleCamera("OTHER"));
        c.selection=roi::Mode::FULL_FRAME;CHECK(c.compatibleCamera("OTHER"));
        for(const auto dimensions:{std::pair<int,int>{640,480},{1280,720},{480,640},{641,479}}){
            const int w=dimensions.first,h=dimensions.second;
            auto box=roi::originalPixels({w*.35,h*.35,w*.65,h*.65},w,h);
            CHECK(box.valid&&std::fabs(box.box.x1-.35)<1e-12);
            auto letter=roi::letterbox(w,h);CHECK(letter.valid);
            auto decoded=roi::letterboxedPixels({w*.35*letter.scale+letter.pad_x,h*.35*letter.scale+letter.pad_y,w*.65*letter.scale+letter.pad_x,h*.65*letter.scale+letter.pad_y},w,h);
            CHECK(decoded.valid&&std::fabs(decoded.box.x1-.35)<2.0/w);
        }
        CHECK(!roi::validBox({std::numeric_limits<double>::quiet_NaN(),.1,.5,.5}));
    });
    std::cout<<"FOOD_ROI_PASS groups="<<groups<<" checks="<<checks<<" synthetic_only=true physical_pass=false\n";
}
} // namespace
int main(int argc,char** argv){
    try{
        if(argc==2&&std::string(argv[1])=="--probe")return probe();
        if(argc!=1)return 2;
        suite();return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
