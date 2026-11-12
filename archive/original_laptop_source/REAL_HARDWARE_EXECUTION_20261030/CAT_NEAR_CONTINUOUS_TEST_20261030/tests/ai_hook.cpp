#include "../jetson/cat_ai_publish.h"
// Compile-only ARM64 probe; not run and no socket opened during verification.
bool compileHook(const char* socket,uint32_t seq,uint64_t captured,float confidence){
    cat_test_ai::Publisher p(socket);
    return p.publish(seq,captured,cat_test_ai::Label::Cat,confidence);
}
