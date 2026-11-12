#include "geometry_validation.h"
#include "geometry_detector.h"
#include <opencv2/opencv.hpp>
#include <openssl/sha.h>
#include <sys/stat.h>
#include <chrono>
#include <cstdio>
#include <ctime>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>

#ifndef FOR_CAT_REPO
#error FOR_CAT_REPO must identify the audited source repository
#endif
namespace gv = geometry_validation;
using namespace behavior_shadow;
namespace {
const std::string repo = FOR_CAT_REPO;
const char* production_hash = "c3651fc3d1331b24a45c6a74b94a883e362fd4ded2412bb8f3ad195f1c443cdc";
const char* engine_hash = "48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb";
const char* detector_source_hash = "9b01288e4b6e450217d3029c2d0b4a3aecafb9dc0e2f87e17289d3e83f5b6366";
std::string read_text(const std::string& path, std::size_t limit = 65536) {
    std::ifstream file(path,std::ios::binary); gv::require(bool(file),"cannot open input file");
    std::string text; char c = 0;
    while (file.get(c)) { text += c; gv::require(text.size() <= limit,"text input exceeds budget"); }
    gv::require(file.eof(),"text read failed"); return text;
}
void write_text(const std::string& path, const std::string& text) {
    std::ofstream file(path,std::ios::binary); file << text; file.close(); gv::require(bool(file),"artifact write failed");
}
std::string sha256(const std::string& path) {
    std::ifstream file(path,std::ios::binary); gv::require(bool(file),"cannot hash input file");
    SHA256_CTX context; SHA256_Init(&context); char data[65536];
    while (file.read(data,sizeof(data)) || file.gcount() > 0)
        SHA256_Update(&context,data,static_cast<std::size_t>(file.gcount()));
    gv::require(file.eof(),"hash read failed"); unsigned char digest[SHA256_DIGEST_LENGTH]; SHA256_Final(digest,&context);
    std::ostringstream out; out << std::hex << std::setfill('0');
    for (unsigned char byte : digest) out << std::setw(2) << static_cast<unsigned>(byte);
    return out.str();
}
void protected_files(const std::string& engine) {
    gv::require(sha256(repo+"/jetson/ai/cat_dog_trt") == production_hash,"production binary hash changed");
    gv::require(sha256(repo+"/jetson/ai/cat_dog_trt.cpp") == detector_source_hash,"audited detector source changed");
    gv::require(sha256(engine) == engine_hash,"engine differs from validated engine");
}
std::string utc() {
    const auto now = std::time(nullptr); std::tm tm{}; gmtime_r(&now,&tm); char result[32];
    gv::require(std::strftime(result,sizeof(result),"%Y-%m-%dT%H:%M:%SZ",&tm) != 0,"UTC formatting failed"); return result;
}
void fresh_output(const std::string& path) {
    const auto slash = path.find_last_of('/'); const auto parent = slash == std::string::npos ? "." : path.substr(0,slash == 0 ? 1 : slash);
    struct stat info{}; gv::require(stat(parent.c_str(),&info) == 0 && S_ISDIR(info.st_mode),"output parent must exist");
    gv::require(mkdir(path.c_str(),0700) == 0,"output directory must be NEW; refusing overwrite");
    write_text(path+"/INCOMPLETE.txt","Run incomplete. Only a finished report/calibration is authoritative.\n");
}
void complete(const std::string& path) { gv::require(std::remove((path+"/INCOMPLETE.txt").c_str()) == 0,"completion marker removal failed"); }
void save_image(const std::string& path,const cv::Mat& image) { gv::require(cv::imwrite(path,image),"image artifact write failed"); }
gv::Dimensions size_of(const cv::Mat& frame) {
    gv::require(!frame.empty() && frame.type() == CV_8UC3,"expected original BGR frame");
    gv::Dimensions d{frame.cols,frame.rows}; gv::dimensions(d); return d;
}
struct Args {
    std::map<std::string,std::string> values;
    bool gui = false, synthetic = false;
    Args(int argc,char** argv,const std::set<std::string>& allowed) {
        for (int i = 2; i < argc; ++i) {
            const std::string key = argv[i]; gv::require(allowed.count(key) != 0,"unknown option for this command");
            gv::require(values.count(key) == 0,"duplicate option");
            if (key == "--gui" || key == "--synthetic") values[key] = "true";
            else { gv::require(++i < argc,"missing option value"); values[key] = argv[i]; }
        }
        gui = values.count("--gui") != 0; synthetic = values.count("--synthetic") != 0;
    }
    std::string get(const std::string& key,const std::string& fallback = "") const {
        const auto i = values.find(key); return i == values.end() ? fallback : i->second;
    }
    std::string need(const std::string& key) const { const auto s = get(key); gv::require(!s.empty(),"required option missing"); return s; }
    std::uint64_t integer(const std::string& key,std::uint64_t fallback,std::uint64_t low,std::uint64_t high) const {
        const auto text = get(key,std::to_string(fallback));
        gv::require(!text.empty() && text.find_first_not_of("0123456789") == std::string::npos,"expected unsigned integer option");
        const auto n = std::stoull(text); gv::require(n >= low && n <= high,"integer option out of range"); return n;
    }
};
gv::Pixels pixel_arg(const std::string& text) {
    std::istringstream s(text); gv::Pixels p; char a = 0,b = 0,c = 0;
    s >> p.x1 >> a >> p.y1 >> b >> p.x2 >> c >> p.y2;
    gv::require(bool(s) && a == ',' && b == ',' && c == ',' && s.peek() == EOF,"ROI format: x1,y1,x2,y2 in original pixels"); return p;
}
void draw_roi(cv::Mat& image,Box b,const std::string& label,const cv::Scalar& color) {
    const auto p = gv::rendered(b,size_of(image));
    cv::rectangle(image,cv::Point(p.x1,p.y1),cv::Point(p.x2-1,p.y2-1),color,2);
    cv::putText(image,label,cv::Point(p.x1,std::max(18,p.y1-5)),cv::FONT_HERSHEY_SIMPLEX,0.5,color,1);
}
cv::Mat overlay(const cv::Mat& original,const Config& c,const Maybe<Track>& track = {},const GeometryObservation& g = {}) {
    cv::Mat out = original.clone();
    draw_roi(out,c.geometry.food_roi,"FOOD_ROI (RED)",cv::Scalar(0,0,255));
    draw_roi(out,c.geometry.water_roi,"WATER_ROI (BLUE)",cv::Scalar(255,0,0));
    if (c.geometry.approach_line_start.present) {
        const auto a = c.geometry.approach_line_start.value,b = c.geometry.approach_line_end.value;
        cv::line(out,cv::Point(static_cast<int>(a.x*out.cols),static_cast<int>(a.y*out.rows)),
                 cv::Point(static_cast<int>(b.x*out.cols),static_cast<int>(b.y*out.rows)),cv::Scalar(255,180,0),1);
    }
    if (track.present && track.value.observed) {
        draw_roi(out,track.value.box,"CAT track="+std::to_string(track.value.id),cv::Scalar(0,255,0));
        const auto p = bbox_bottom_center(track.value.box);
        cv::circle(out,cv::Point(std::min(out.cols-1,static_cast<int>(p.x*out.cols)),std::min(out.rows-1,static_cast<int>(p.y*out.rows))),4,cv::Scalar(0,255,255),-1);
        cv::putText(out,name(g.state),cv::Point(8,out.rows-28),cv::FONT_HERSHEY_SIMPLEX,0.5,cv::Scalar(0,255,255),1);
    }
    cv::putText(out,"GEOMETRY ONLY - NOT EATING/DRINKING",cv::Point(8,out.rows-8),cv::FONT_HERSHEY_SIMPLEX,0.45,cv::Scalar(255,255,255),1);
    return out;
}
struct Calibration { Config config; gv::Dimensions dimensions; std::string config_hash; };
Calibration calibration(const std::string& folder,bool synthetic) {
    Calibration c; const auto path = folder+"/roi.candidate.json";
    c.config = load_config_json(read_text(path),synthetic); c.config_hash = sha256(path);
    cv::FileStorage metadata(folder+"/calibration.json",cv::FileStorage::READ|cv::FileStorage::FORMAT_JSON);
    gv::require(metadata.isOpened(),"missing calibration provenance");
    const auto number = [&](const char* key) {
        const auto n = metadata[key]; gv::require(n.isInt(),"calibration dimensions/version must be integers"); return static_cast<int>(n);
    };
    const auto string = [&](const char* key) {
        const auto n = metadata[key]; gv::require(n.isString(),"missing calibration string"); return static_cast<std::string>(n);
    };
    gv::require(number("schema_version") == 1 && number("config_schema_version") == 2,"calibration schema mismatch");
    c.dimensions = {number("source_width"),number("source_height")}; gv::dimensions(c.dimensions);
    gv::require(string("config_sha256") == c.config_hash,"config changed since calibration; create a new reviewed candidate");
    gv::require(string("food_bowl_color") == "RED" && string("water_bowl_color") == "BLUE","calibration semantic mismatch");
    gv::require(string("coordinate_system") == "normalized_original_camera_frame","wrong calibration coordinate domain");
    return c;
}
void calibrate(const Args& a) {
    const auto image_path = a.need("--image"); const auto image = cv::imread(image_path); const auto d = size_of(image);
    Config c; if (!a.get("--base-config").empty()) c = load_config_json(read_text(a.get("--base-config")),a.synthetic);
    gv::require(a.gui != (!a.get("--food").empty() || !a.get("--water").empty()),"choose GUI or explicit FOOD and WATER coordinates");
    gv::Pixels food,water;
    if (a.gui) {
        std::cerr << "Select RED FOOD region, then BLUE WATER region; original-frame coordinates. ESC cancels.\n";
        const auto f = cv::selectROI("FOOD_ROI = RED (human review)",image,false,false);
        const auto w = cv::selectROI("WATER_ROI = BLUE (human review)",image,false,false);
        cv::destroyAllWindows(); food = {f.x,f.y,f.x+f.width,f.y+f.height}; water = {w.x,w.y,w.x+w.width,w.y+w.height};
    } else { food = pixel_arg(a.need("--food")); water = pixel_arg(a.need("--water")); }
    c.geometry.food_roi = gv::normalized(food,d); c.geometry.water_roi = gv::normalized(water,d);
    const auto json = gv::config_json(c,a.synthetic); static_cast<void>(load_config_json(json,a.synthetic));
    const auto out = a.need("--out"); fresh_output(out); write_text(out+"/roi.candidate.json",json);
    std::ostringstream metadata;
    metadata << "{\"schema_version\":1,\"config_schema_version\":2,\"purpose\":\"GEOMETRY_CALIBRATION\","
      << "\"coordinate_system\":\"normalized_original_camera_frame\",\"source_width\":" << d.width << ",\"source_height\":" << d.height
      << ",\"calibrated_utc\":" << gv::quote(utc()) << ",\"source_image\":" << gv::quote(image_path)
      << ",\"source_reference\":" << gv::quote(a.get("--source-reference",image_path)) << ",\"source_image_sha256\":" << gv::quote(sha256(image_path))
      << ",\"config_sha256\":" << gv::quote(sha256(out+"/roi.candidate.json"))
      << ",\"base_config_sha256\":" << gv::quote(a.get("--base-config").empty()?"":sha256(a.get("--base-config")))
      << ",\"threshold_origin\":" << gv::quote(a.get("--base-config").empty()?"DEFAULTS_UNCALIBRATED":"USER_SUPPLIED_BASE_CONFIG")
      << ",\"food_bowl_color\":\"RED\",\"water_bowl_color\":\"BLUE\",\"food_roi\":" << gv::box_json(c.geometry.food_roi)
      << ",\"water_roi\":" << gv::box_json(c.geometry.water_roi)
      << ",\"review_status\":\"HUMAN_OVERLAY_REVIEW_REQUIRED\",\"source_kind\":" << gv::quote(a.synthetic ? "SYNTHETIC_FIXTURE" : "USER_SUPPLIED_IMAGE") << "}\n";
    write_text(out+"/calibration.json",metadata.str()); save_image(out+"/overlay.png",overlay(image,c));
    write_text(out+"/REVIEW.md","# ROI human review\n\nReview overlay.png against the ORIGINAL image. RED must be FOOD and BLUE must be WATER.\nCoordinates were specified by the operator, not inferred from colors.\nIf camera position/crop/resolution changes, review and recalibrate. Thresholds are unvalidated defaults or the supplied base config.\n");
    complete(out); std::cout << "Candidate written: " << out << "; inspect overlay.png (no automatic bowl identity verification).\n";
}
void verify_overlay(const Args& a) {
    const auto c = calibration(a.need("--calibration"),a.synthetic); const auto path = a.need("--image"); const auto frame = cv::imread(path);
    gv::same_dimensions(size_of(frame),c.dimensions); const auto out = a.need("--out"); fresh_output(out);
    save_image(out+"/overlay.png",overlay(frame,c.config));
    write_text(out+"/verification.json","{\"purpose\":\"GEOMETRY_OVERLAY_HUMAN_REVIEW\",\"config_sha256\":"+gv::quote(c.config_hash)+
               ",\"source_image_sha256\":"+gv::quote(sha256(path))+",\"source_image\":"+gv::quote(path)+",\"reviewed_automatically\":false}\n");
    complete(out);
}
void capture_frame(const Args& a) {
    const auto video = a.get("--video"), device = a.get("--camera"); gv::require(video.empty() != device.empty(),"choose --video or --camera");
    const auto index = a.integer("--frame-index",0,0,999999); cv::Mat frame; double pts = 0;
    if (!video.empty()) {
        cv::VideoCapture cap(video); gv::require(cap.isOpened(),"video open failed");
        for (std::uint64_t i = 0; i <= index; ++i) gv::require(cap.read(frame) && !frame.empty(),"requested video frame unavailable");
        pts = cap.get(cv::CAP_PROP_POS_MSEC);
    } else {
        gv::require(index == 0,"camera capture supports only frame-index 0");
        gv::LiveSource live(device); const auto begin = std::chrono::steady_clock::now(); Millis stamp = 0;
        while (frame.empty() && std::chrono::steady_clock::now()-begin < std::chrono::seconds(10)) live.read(frame,stamp);
        gv::require(!frame.empty(),"camera capture timeout"); pts = static_cast<double>(stamp);
    }
    const auto d = size_of(frame); const auto out = a.need("--out"); fresh_output(out); save_image(out+"/original.png",frame);
    write_text(out+"/capture.json","{\"purpose\":\"ORIGINAL_FRAME_CAPTURE\",\"source\":"+gv::quote(video.empty()?device:video)+
      ",\"frame_index\":"+std::to_string(index)+",\"raw_source_ms\":"+(std::isfinite(pts)?std::to_string(pts):"null")+
      ",\"width\":"+std::to_string(d.width)+",\"height\":"+std::to_string(d.height)+",\"captured_utc\":"+gv::quote(utc())+
      ",\"source_kind\":"+gv::quote(a.synthetic?"SYNTHETIC_FIXTURE":(video.empty()?"REAL_CAMERA_CAPTURE":"USER_SUPPLIED_VIDEO"))+"}\n"); complete(out);
}
using Manual = std::map<std::uint64_t,std::vector<Detection>>;
Manual manual_boxes(const std::string& path,gv::Dimensions d) {
    Manual result; std::istringstream csv(read_text(path,16*1024*1024)); std::string line; std::getline(csv,line);
    if (!line.empty() && line.back() == '\r') line.pop_back();
    gv::require(line == "frame_index,class_id,confidence,x1,y1,x2,y2","manual CSV header mismatch"); std::size_t rows = 0;
    while (std::getline(csv,line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        std::replace(line.begin(),line.end(),',',' '); std::istringstream row(line);
        std::uint64_t index = 0; int object = 0; double confidence = 0; gv::Pixels p;
        row >> index >> object >> confidence >> p.x1 >> p.y1 >> p.x2 >> p.y2;
        const bool parsed = bool(row); row >> std::ws;
        gv::require(parsed && row.eof() && index < 1000000 && (object == 15 || object == 16) &&
                    std::isfinite(confidence) && confidence >= 0 && confidence <= 1,"invalid manual CSV row");
        gv::require(++rows <= 200000 && result[index].size() < 1024,"manual CSV row budget exceeded");
        result[index].push_back({object == 15 ? Object::Cat : Object::Dog,confidence,gv::normalized(p,d)});
    } return result;
}
struct Evidence { std::uint64_t frame = 0; Millis timestamp = 0; };
void validate_video(const Args& a,bool live) {
    const auto cal = calibration(a.need("--calibration"),a.synthetic); const auto& c = cal.config;
    const auto source = a.need(live ? "--camera" : "--video");
    const auto engine = a.get("--engine",repo+"/models/tensorrt/yolov8n_320_fp16.engine"); protected_files(engine);
    const auto manual_path = a.get("--detections"); const auto mode = a.get("--detector",manual_path.empty()?"trt":"manual");
    gv::require(mode == "trt" || mode == "none" || mode == "manual","detector must be trt, none, or manual");
    gv::require((mode == "manual") == !manual_path.empty() && !(live && mode == "manual"),"manual mode requires CSV and recorded video");
    const auto max_frames = a.integer("--max-frames",18000,1,100000), every = a.integer("--every",1,1,100);
    const auto seconds = a.integer("--seconds",15,1,300);
    std::unique_ptr<gv::Detector> detector; if (mode == "trt") detector.reset(new gv::Detector(engine));
    Manual manual; if (mode == "manual") manual = manual_boxes(manual_path,cal.dimensions);
    cv::VideoCapture video; std::unique_ptr<gv::LiveSource> camera; double fps = 0, advertised_frames = 0;
    if (live) camera.reset(new gv::LiveSource(source));
    else { video.open(source); gv::require(video.isOpened(),"video open failed"); fps = video.get(cv::CAP_PROP_FPS); advertised_frames = video.get(cv::CAP_PROP_FRAME_COUNT); }
    gv::VideoClock clock(fps); SingleCatTracker tracker(c.tracker); Roi context = Roi::None;
    const auto out = a.need("--out"); fresh_output(out); write_text(out+"/config.used.json",read_text(a.need("--calibration")+"/roi.candidate.json"));
    write_text(out+"/calibration.used.json",read_text(a.need("--calibration")+"/calibration.json"));
    std::ofstream log(out+"/frames.jsonl"); log.imbue(std::locale::classic()); log << std::setprecision(17);
    gv::Distribution food_dist,water_dist;
    std::uint64_t decoded = 0, processed = 0, raw_cats = 0, eligible_cats = 0, observed = 0, misses = 0, ambiguous = 0;
    std::uint64_t id_changes = 0, missed_episodes = 0, reacquired = 0, expired = 0, current_run = 0, longest_run = 0, last_id = 0;
    std::map<std::string,std::uint64_t> transitions;
    std::map<std::string,Evidence> evidence;
    bool previous_observed = false, previous_present = false, ever_observed = false, eof = false;
    Millis first_ms = 0,last_ms = 0,near_food_ms = 0,near_water_ms = 0,unassigned_ms = 0;
    GeometryObservation previous_geometry; GeometryState previous_state = GeometryState::Far;
    double nearest_food = 2,nearest_water = 2;
    const auto begin = std::chrono::steady_clock::now();
    while (processed < max_frames && decoded < 1000000) {
        if (live && std::chrono::steady_clock::now()-begin >= std::chrono::seconds(seconds)) break;
        cv::Mat frame; Millis stamp = 0; double raw_pts = 0;
        if (live) { if (!camera->read(frame,stamp)) continue; }
        else {
            if (!video.read(frame) || frame.empty()) { eof = true; break; }
            raw_pts = video.get(cv::CAP_PROP_POS_MSEC); stamp = clock.next(raw_pts);
        }
        gv::same_dimensions(size_of(frame),cal.dimensions); const auto index = decoded++;
        if (index % every != 0) continue;
        std::vector<Detection> detections;
        if (detector) detections = detector->infer(frame);
        else if (mode == "manual") { const auto i = manual.find(index); if (i != manual.end()) detections = i->second; }
        const auto before_id = tracker.track().present ? tracker.track().value.id : 0;
        const auto track = tracker.update(stamp,detections);
        if (!track.present || track.value.id != before_id) context = Roi::None;
        const bool seen = track.present && track.value.observed && !tracker.ambiguous();
        GeometryObservation geometry;
        if (seen) geometry = observe_geometry(track.value,c.geometry,context);
        if (tracker.ambiguous()) { geometry.state = GeometryState::Ambiguous; geometry.roi = Roi::Ambiguous; }
        const bool unclear = tracker.ambiguous() || geometry.state == GeometryState::Ambiguous;
        context = seen && geometry.near && !unclear ? geometry.roi : Roi::None;
        if (processed == 0) first_ms = stamp;
        else {
            const Millis delta = stamp-last_ms;
            if (previous_observed && delta <= c.temporal.max_observation_gap_ms && previous_geometry.near) {
                if (previous_geometry.roi == Roi::Food) near_food_ms += delta;
                else if (previous_geometry.roi == Roi::Water) near_water_ms += delta;
            } else unassigned_ms += delta;
        }
        std::uint64_t cats_this_frame = 0,eligible_this_frame = 0; Maybe<double> confidence;
        for (const auto& d : detections) if (d.object == Object::Cat) {
            ++cats_this_frame; if (d.confidence >= c.tracker.min_confidence) { ++eligible_this_frame; if (seen) confidence = Maybe<double>(d.confidence); }
        }
        raw_cats += cats_this_frame; eligible_cats += eligible_this_frame;
        if (track.present && last_id != 0 && track.value.id != last_id) ++id_changes;
        if (track.present) last_id = track.value.id;
        if (seen) { ++observed; longest_run = std::max(longest_run,++current_run); }
        else { current_run = 0; if (track.present) ++misses; }
        if (previous_observed && !seen) ++missed_episodes;
        if (ever_observed && !previous_observed && seen) ++reacquired;
        if (previous_present && !track.present) ++expired;
        if (before_id != 0 && track.present && track.value.id != before_id) ++expired;
        if (unclear) ++ambiguous;
        if (geometry.state != previous_state) ++transitions[name(geometry.state)];
        if (seen) { food_dist.add(geometry.food_distance); water_dist.add(geometry.water_distance); }
        const auto annotate = [&] { return overlay(frame,c,track,geometry); };
        const auto save = [&](const std::string& tag,bool replace_existing = false) {
            if (evidence.count(tag) == 0 || replace_existing) {
                save_image(out+"/"+gv::artifact_name(tag),annotate()); evidence[tag] = {index,stamp};
            }
        };
        if (seen) {
            save("first_cat");
            if (geometry.food_distance < nearest_food) { nearest_food = geometry.food_distance; save("nearest_food",true); }
            if (geometry.water_distance < nearest_water) { nearest_water = geometry.water_distance; save("nearest_water",true); }
            if (geometry.state == GeometryState::ApproachingFood) save("approaching_food");
            if (geometry.state == GeometryState::ApproachingWater) save("approaching_water");
            if (geometry.state == GeometryState::Leaving) save("leaving");
        }
        if (unclear) save("ambiguous");
        if (previous_observed && !seen) save("track_lost");
        if (ever_observed && !previous_observed && seen) save("reacquired");
        log << "{\"frame_index\":" << index << ",\"timestamp_ms\":" << stamp << ",\"raw_pts_ms\":";
        if (live || !std::isfinite(raw_pts)) log << "null"; else log << raw_pts;
        log << ",\"cat_detections\":" << cats_this_frame << ",\"eligible_cats\":" << eligible_this_frame
            << ",\"track_id\":" << (track.present?std::to_string(track.value.id):"null") << ",\"cat_observed\":" << (seen?"true":"false")
            << ",\"cat_confidence\":" << (confidence.present?std::to_string(confidence.value):"null")
            << ",\"bbox\":" << (track.present?gv::box_json(track.value.box):"null") << ",\"geometry_valid\":" << (seen?"true":"false")
            << ",\"geometry_state\":" << gv::quote(name(geometry.state)) << ",\"roi\":" << gv::quote(name(geometry.roi))
            << ",\"food_distance\":" << (seen?std::to_string(geometry.food_distance):"null")
            << ",\"water_distance\":" << (seen?std::to_string(geometry.water_distance):"null")
            << ",\"food_body_overlap\":" << (seen?std::to_string(gv::body_overlap(track.value.box,c.geometry.food_roi)):"null")
            << ",\"water_body_overlap\":" << (seen?std::to_string(gv::body_overlap(track.value.box,c.geometry.water_roi)):"null")
            << ",\"reference\":" << (seen?("{\"x\":"+std::to_string(geometry.reference.x)+",\"y\":"+std::to_string(geometry.reference.y)+"}"):"null")
            << ",\"detections\":[";
        bool comma = false;
        for (const auto& d : detections) {
            if (comma) log << ',';
            comma = true;
            log << "{\"class_id\":" << (d.object == Object::Cat ? 15 : 16) << ",\"confidence\":" << d.confidence << ",\"bbox\":" << gv::box_json(d.box) << '}';
        }
        log << "],\"behavior_observation\":null,\"behavior_events\":[]}\n";
        gv::require(bool(log),"frame log write failed");
        if (a.gui) { cv::imshow("GEOMETRY VALIDATION ONLY",annotate()); if ((cv::waitKey(1)&255) == 'q') { ++processed; last_ms = stamp; break; } }
        ++processed; last_ms = stamp; previous_geometry = geometry; previous_state = geometry.state;
        previous_present = track.present; previous_observed = seen; ever_observed = ever_observed || seen;
    }
    log.close(); gv::require(bool(log),"frame log close failed"); if (a.gui) cv::destroyAllWindows();
    gv::require(processed > 0,"no frames processed"); protected_files(engine);
    const bool early_decode = eof && std::isfinite(advertised_frames) && advertised_frames > static_cast<double>(decoded)+1;
    const std::string termination = early_decode?"POSSIBLE_EARLY_DECODE_FAILURE":(eof?"DECODE_EOF":(processed>=max_frames?"FRAME_LIMIT":"TIME_OR_OPERATOR_LIMIT"));
    std::ostringstream report; report.imbue(std::locale::classic()); report << std::setprecision(17);
    report << "{\"schema_version\":1,\"purpose\":\"GEOMETRY VALIDATION\",\"shadow_only\":true,\"behavior_validation\":false,\"behavior_events\":0,"
      << "\"source_kind\":" << gv::quote(a.synthetic?"SYNTHETIC_FIXTURE":(live?"LIVE_CAMERA":"USER_SUPPLIED_VIDEO"))
      << ",\"detector_mode\":" << gv::quote(mode) << ",\"source\":" << gv::quote(source)
      << ",\"source_sha256\":" << (live?"null":gv::quote(sha256(source))) << ",\"manual_boxes_sha256\":" << (manual_path.empty()?"null":gv::quote(sha256(manual_path)))
      << ",\"created_utc\":" << gv::quote(utc()) << ",\"config_sha256\":" << gv::quote(cal.config_hash)
      << ",\"width\":" << cal.dimensions.width << ",\"height\":" << cal.dimensions.height
      << ",\"decoded_frames\":" << decoded << ",\"frames_processed\":" << processed << ",\"sample_every\":" << every
      << ",\"termination\":" << gv::quote(termination) << ",\"possible_decode_failure\":" << (early_decode?"true":"false")
      << ",\"timestamp_policy\":" << gv::quote(live?"capture_received_monotonic_ms":"media_PTS_then_anchored_FPS_fallback")
      << ",\"timestamp_fallback_frames\":" << clock.fallback_frames() << ",\"sampled_span_ms\":" << last_ms-first_ms
      << ",\"cat_detections\":" << raw_cats << ",\"eligible_cat_detections\":" << eligible_cats << ",\"observed_track_frames\":" << observed
      << ",\"observed_track_fraction\":" << static_cast<double>(observed)/static_cast<double>(processed)
      << ",\"longest_observed_run_frames\":" << longest_run << ",\"track_id_changes\":" << id_changes
      << ",\"temporary_miss_frames\":" << misses << ",\"miss_episodes\":" << missed_episodes << ",\"reacquisitions\":" << reacquired << ",\"track_expirations\":" << expired
      << ",\"ambiguous_frames\":" << ambiguous << ",\"near_food_ms\":" << near_food_ms << ",\"near_water_ms\":" << near_water_ms
      << ",\"unassigned_interval_ms\":" << unassigned_ms << ",\"approaching_food_transitions\":" << transitions["APPROACHING_FOOD"]
      << ",\"approaching_water_transitions\":" << transitions["APPROACHING_WATER"] << ",\"leaving_transitions\":" << transitions["LEAVING"]
      << ",\"food_distance\":" << food_dist.json() << ",\"water_distance\":" << water_dist.json()
      << ",\"production_binary_sha256\":" << gv::quote(production_hash) << ",\"engine_sha256\":" << gv::quote(engine_hash)
      << ",\"detector_source_sha256\":" << gv::quote(detector_source_hash) << ",\"threshold_policy\":\"UNCHANGED_FROM_CONFIG; NO_AUTO_OPTIMIZATION\",\"evidence\":[";
    bool comma = false;
    for (const auto& entry : evidence) {
        if (comma) report << ',';
        comma = true;
        report << "{\"reason\":" << gv::quote(entry.first) << ",\"path\":" << gv::quote(gv::artifact_name(entry.first))
          << ",\"frame_index\":" << entry.second.frame << ",\"timestamp_ms\":" << entry.second.timestamp << '}';
    }
    report << "]}\n"; write_text(out+"/report.json",report.str());
    std::ostringstream md;
    md << "# GEOMETRY VALIDATION\n\nNot behavior validation. No EATING/DRINKING observation source or events.\n\n"
       << "- Source kind: " << (a.synthetic?"SYNTHETIC_FIXTURE":(live?"LIVE_CAMERA":"USER_SUPPLIED_VIDEO")) << "\n- Detector mode: " << mode
       << "\n- Frames processed: " << processed << " / decoded: " << decoded << "\n- Termination: " << termination
       << "\n- CAT detections: " << raw_cats << " (tracker-eligible: " << eligible_cats << ")\n- Observed-track frames: " << observed
       << "\n- Track ID changes: " << id_changes << "\n- Miss episodes/reacquisitions: " << missed_episodes << '/' << reacquired
       << "\n- Ambiguous frames: " << ambiguous << "\n- Near FOOD/WATER ms: " << near_food_ms << '/' << near_water_ms
       << "\n- PTS fallback frames: " << clock.fallback_frames()
       << "\n\nNear times are left-held sampled geometry intervals, capped by max_observation_gap_ms. No tail extrapolation."
       << " Distances use normalized bbox_bottom_center, not head position or cm."
       << " FPS fallback is approximate for VFR media; review timestamps. frames.jsonl contains all sampled observations.\n\n## Human-review images\n";
    for (const auto& entry : evidence) md << "- [" << entry.first << "](" << gv::artifact_name(entry.first) << ") frame=" << entry.second.frame << " ms=" << entry.second.timestamp << '\n';
    if (evidence.empty()) md << "No qualifying CAT/geometry evidence; no representative CAT images fabricated.\n";
    write_text(out+"/report.md",md.str());
    write_text(out+"/threshold_review.md","# Threshold review (no auto tuning)\n\nBEFORE: config.used.json (bound by config SHA256 in report).\nCANDIDATE: none proposed automatically.\nREASON: compare multiple reviewed sessions before changing defaults.\nAFTER: unchanged.\n\nReview geometry.near_distance, exit_distance, min_body_overlap, min_motion_per_second (shared approaching/leaving gate), motion_window_ms; tracker.min_confidence, min_iou, max_centroid_distance, ttl_ms.\nCreate a new candidate via calibrate --base-config with the same human-reviewed pixel ROIs. Never edit a hash-bound calibration in place.\n");
    complete(out); std::cout << "GEOMETRY VALIDATION report: " << out << "/report.md\n";
    gv::require(!early_decode,"possible early decode failure; report retained for review");
}
} // namespace
int main(int argc,char** argv) {
    try {
        gv::require(argc >= 2,"commands: capture, calibrate, overlay, video, live, check-config, self-test"); const std::string command = argv[1];
        if (command == "self-test") { gv::require(argc == 2,"self-test takes no options"); std::cout << "2 named detector suites: 4-shape letterbox/preprocess and class/NMS contract; " << gv::detector_coordinate_tests() << " assertions PASS\n"; return 0; }
        if (command == "capture") capture_frame(Args(argc,argv,{"--video","--camera","--frame-index","--out","--synthetic"}));
        else if (command == "calibrate") calibrate(Args(argc,argv,{"--image","--food","--water","--gui","--out","--base-config","--source-reference","--synthetic"}));
        else if (command == "overlay") verify_overlay(Args(argc,argv,{"--image","--calibration","--out","--synthetic"}));
        else if (command == "video" || command == "live") validate_video(Args(argc,argv,command == "video" ?
            std::set<std::string>{"--video","--calibration","--out","--detector","--detections","--engine","--max-frames","--every","--gui","--synthetic"} :
            std::set<std::string>{"--camera","--calibration","--out","--detector","--engine","--max-frames","--every","--seconds","--gui"}),command == "live");
        else if (command == "check-config") { const Args a(argc,argv,{"--config","--synthetic"}); load_config_json(read_text(a.need("--config")),a.synthetic); std::cout << "ROI parser compatibility PASS\n"; }
        else throw std::invalid_argument("unknown geometry command");
        return 0;
    } catch (const std::exception& error) { std::cerr << "GEOMETRY_ERROR: " << error.what() << '\n'; return 2; }
}
