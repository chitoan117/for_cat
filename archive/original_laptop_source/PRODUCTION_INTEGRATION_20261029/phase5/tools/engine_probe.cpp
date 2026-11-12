// Owner-run only after legacy AI is stopped; never opens camera or runs inference.
#include <NvInfer.h>
#include <NvInferVersion.h>
#include <fstream>
#include <iostream>
#include <memory>
#include <vector>
#include "latency_support.h"
class Logger:public nvinfer1::ILogger{void log(Severity s,const char* m)noexcept override{if(s<=Severity::kWARNING)std::cerr<<m<<'\n';}};
template<class T>struct Destroy{void operator()(T* p)const{if(p)p->destroy();}};
int main(int argc,char**argv){
 if(argc!=2)return 2;
 try{
  using namespace nvinfer1;
  if(getInferLibVersion()/1000!=NV_TENSORRT_MAJOR)throw std::runtime_error("TensorRT runtime/header major mismatch");
  std::ifstream f(argv[1],std::ios::binary|std::ios::ate);
  if(!f || f.tellg()<=0 || f.tellg()>512*1024*1024)throw std::runtime_error("engine file bound");
  std::vector<char> bytes(static_cast<size_t>(f.tellg()));f.seekg(0);if(!f.read(bytes.data(),bytes.size()))throw std::runtime_error("engine read");
  Logger logger;std::unique_ptr<nvinfer1::IRuntime,Destroy<nvinfer1::IRuntime>> r(nvinfer1::createInferRuntime(logger));
  if(!r)throw std::runtime_error("TensorRT runtime initialization");
  std::unique_ptr<nvinfer1::ICudaEngine,Destroy<nvinfer1::ICudaEngine>> e(r->deserializeCudaEngine(bytes.data(),bytes.size()));
  if(!e)throw std::runtime_error("engine deserialize");
  std::vector<latency::Binding> bindings;
  for(int i=0;i<e->getNbBindings();++i){
    if(e->getBindingFormat(i)!=nvinfer1::TensorFormat::kLINEAR || e->getBindingVectorizedDim(i)!=-1)throw std::runtime_error("vectorized engine storage");
    latency::Binding b{e->bindingIsInput(i),e->getBindingDataType(i)==nvinfer1::DataType::kFLOAT,{}};
    auto dims=e->getBindingDimensions(i);for(int j=0;j<dims.nbDims;++j)b.dimensions.push_back(dims.d[j]);bindings.push_back(b);
  }
  auto error=latency::binding_error(bindings,e->hasImplicitBatchDimension());if(!error.empty())throw std::runtime_error(error);
  std::cout<<"{\"engine_contract\":\"PASS\",\"input\":\"1x3x320x320 FLOAT32\",\"output\":\"1x84x2100 FLOAT32\",\"classes\":\"COCO CAT15 DOG16\",\"inference_run\":false,\"camera_opened\":false}\n";
 }catch(const std::exception&e){std::cerr<<"ENGINE_PROBE_FAIL "<<e.what()<<'\n';return 1;}
}
