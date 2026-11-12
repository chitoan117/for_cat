#pragma once
#include <cmath>
#include <string>
#include "food_roi.h"
namespace forcat {
class RoiSpecies {
 food_roi::Config config_;int width_=0,height_=0;bool invalid_=false,cat_=false,dog_=false;
 double cat_score_=0,dog_score_=0;
 public:
 RoiSpecies(const food_roi::Config& config,int width,int height):config_(config),width_(width),height_(height),invalid_(!food_roi::validFrame(width,height)){}
 // Compatibility for callers explicitly requesting an enabled ROI.
 RoiSpecies(bool ready,double x1,double y1,double x2,double y2):width_(640),height_(480){
   config_.selection=food_roi::Mode::ROI_ENABLED;config_.coordinates_present=true;config_.calibrated=ready;
   config_.review_id="LEGACY_EXPLICIT_ROI";config_.roi={x1,y1,x2,y2};
 }
 food_roi::Relation box(bool dog,bool cat,double score,double a,double b,double c,double d){
   if(!dog&&!cat)return food_roi::Relation::OUTSIDE_ROI;
   if(!std::isfinite(score)||score<0||score>1){invalid_=true;return food_roi::Relation::INVALID;}
   const auto relation=food_roi::evaluate(config_,{a,b,c,d},width_,height_);
   if(relation==food_roi::Relation::INVALID){invalid_=true;return relation;}
   if(score<.35 || (relation!=food_roi::Relation::IN_ROI&&relation!=food_roi::Relation::FULL_FRAME))return relation;
   if(dog){dog_=true;if(score>dog_score_)dog_score_=score;}
   if(cat){cat_=true;if(score>cat_score_)cat_score_=score;}
   return relation;
 }
 bool eligible()const{return !invalid_&&config_.decisionAllowed();}
 std::string species()const{return !eligible()?"UNKNOWN":dog_?"DOG":cat_?"CAT":"NONE";}
 bool detected()const{return eligible()&&(cat_||dog_);}double confidence()const{return dog_?dog_score_:cat_score_;}
 bool invalid()const{return invalid_;}bool catPresent()const{return cat_;}bool dogPresent()const{return dog_;}
};
}
