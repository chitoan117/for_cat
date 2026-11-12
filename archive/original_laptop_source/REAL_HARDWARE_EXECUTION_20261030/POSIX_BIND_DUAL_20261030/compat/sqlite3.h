#pragma once
// Public SQLite C ABI for Windows CI and explicit compile-only Linux syntax CI.
// Real POSIX builds use installed sqlite3.h, never this include directory.
#if !defined(FORCAT_BRIDGE_TEST) && !defined(FORCAT_POSIX_SYNTAX_CHECK)
#error "SQLite ABI shim is CI-only"
#endif
extern "C" {
struct sqlite3;struct sqlite3_stmt;
typedef long long sqlite3_int64;
typedef void (*sqlite3_destructor_type)(void*);
int sqlite3_open_v2(const char*,sqlite3**,int,const char*);
int sqlite3_close(sqlite3*);
int sqlite3_busy_timeout(sqlite3*,int);
int sqlite3_exec(sqlite3*,const char*,int(*)(void*,int,char**,char**),void*,char**);
void sqlite3_free(void*);
const char* sqlite3_errmsg(sqlite3*);
int sqlite3_prepare_v2(sqlite3*,const char*,int,sqlite3_stmt**,const char**);
int sqlite3_bind_text(sqlite3_stmt*,int,const char*,int,sqlite3_destructor_type);
int sqlite3_bind_int64(sqlite3_stmt*,int,sqlite3_int64);
int sqlite3_step(sqlite3_stmt*);
int sqlite3_finalize(sqlite3_stmt*);
const unsigned char* sqlite3_column_text(sqlite3_stmt*,int);
int sqlite3_column_bytes(sqlite3_stmt*,int);
int sqlite3_column_int(sqlite3_stmt*,int);
sqlite3_int64 sqlite3_column_int64(sqlite3_stmt*,int);
int sqlite3_changes(sqlite3*);
const char* sqlite3_libversion();
}
#define SQLITE_OK 0
#define SQLITE_BUSY 5
#define SQLITE_LOCKED 6
#define SQLITE_ROW 100
#define SQLITE_DONE 101
#define SQLITE_OPEN_READWRITE 2
#define SQLITE_OPEN_CREATE 4
#define SQLITE_OPEN_FULLMUTEX 0x10000
#define SQLITE_TRANSIENT ((sqlite3_destructor_type)-1)
