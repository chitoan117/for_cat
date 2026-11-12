// Only new fixed-camera candidate tests. Animal boxes below are SYNTHETIC.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include "roi_species.h"
namespace roi=forcat::food_roi;
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);std::exit(1);}}while(0)
int main(int argc,char** argv){
 CHECK(argc==2);std::ifstream file(argv[1]);CHECK(file.good());const std::string text((std::istreambuf_iterator<char>(file)),{});
 auto candidate=roi::parseConfig(text);
 CHECK(candidate.syntax_valid&&candidate.coordinates_present&&roi::validBox(candidate.roi));
 CHECK(candidate.reference_width==1920&&candidate.reference_height==1080);
 CHECK(candidate.selection==roi::Mode::FULL_FRAME&&candidate.decisionAllowed()&&!candidate.calibrated&&candidate.review_id.empty());
 CHECK(candidate.roi.x1==.02&&candidate.roi.y1==.40&&candidate.roi.x2==.75&&candidate.roi.y2==1);
 auto unreviewed=roi::parseConfig(text,roi::Mode::ROI_ENABLED);
 CHECK(!unreviewed.decisionAllowed());
 CHECK(roi::evaluate(unreviewed,{.15,.45,.65,1},1920,1080)==roi::Relation::BLOCKED);
 auto synthetic=unreviewed;synthetic.calibrated=true;synthetic.review_id="SYNTHETIC_CANDIDATE_GEOMETRY_ONLY";
 CHECK(synthetic.decisionAllowed());
 for(const auto dims:{std::pair<int,int>{1920,1080},{1280,720},{640,360}}){
   const roi::Box near{.15,.45,.65,1};
   CHECK(roi::evaluate(synthetic,near,dims.first,dims.second)==roi::Relation::IN_ROI);
   CHECK(roi::evaluate(synthetic,{.2,.05,.5,.35},dims.first,dims.second)==roi::Relation::OUTSIDE_ROI);
   CHECK(roi::evaluate(synthetic,{.78,.5,.98,.95},dims.first,dims.second)==roi::Relation::OUTSIDE_ROI);
   CHECK(roi::evaluate(synthetic,{.74,.6,.9,.95},dims.first,dims.second)==roi::Relation::OUTSIDE_ROI);
   CHECK(roi::evaluate(synthetic,{.75,.5,.9,.8},dims.first,dims.second)==roi::Relation::OUTSIDE_ROI);
   auto pixels=roi::originalPixels({near.x1*dims.first,near.y1*dims.second,near.x2*dims.first,near.y2*dims.second},dims.first,dims.second);
   CHECK(pixels.valid&&roi::evaluate(synthetic,pixels.box,dims.first,dims.second)==roi::Relation::IN_ROI);
 }
 forcat::RoiSpecies scene(synthetic,1920,1080);
 CHECK(scene.species()=="NONE"); // the supplied picture contains no labeled animal bbox
 CHECK(scene.box(false,false,.99,.45,.28,.58,.7)==roi::Relation::OUTSIDE_ROI&&scene.species()=="NONE"); // bottle is not an animal class
 scene.box(false,true,.9,.15,.45,.65,1);CHECK(scene.species()=="CAT");
 scene.box(true,false,.9,.2,.5,.7,1);CHECK(scene.species()=="DOG");
 // Why a tight rectangle around only the visible metal bowl is inadequate for
 // whole-animal boxes: it rejects a plausible near-animal BODY bbox.
 auto tight=synthetic;tight.roi={0,.76,.64,1};
 CHECK(roi::evaluate(tight,{.15,.45,.65,1},1920,1080)==roi::Relation::OUTSIDE_ROI);
 // Explicitly retain the known limitation: a very tall/large animal may still
 // be rejected even by the expanded candidate; the photograph cannot settle it.
 CHECK(roi::evaluate(synthetic,{0,0,1,1},1920,1080)==roi::Relation::OUTSIDE_ROI);
 forcat::RoiSpecies global(candidate,1920,1080);global.box(false,true,.9,0,0,1,1);
 CHECK(global.species()=="CAT");
 CHECK(roi::evaluate(synthetic,{.1,.4,.8,1.1},1920,1080)==roi::Relation::INVALID);
 std::printf("FIXED_CAMERA_ROI_CANDIDATE_PASS assertions=%u synthetic_boxes_only=true real_animal_validation=false\n",checks);
}
