"""SCons post-build observation, never uploader. Captures actual flash addresses."""
Import('env')
import json
from pathlib import Path
def emit(source,target,env):
    def resolved(value):return env.subst(str(value))
    data={'profile':env['PIOENV'],'board':env['BOARD'],'platform_dir':str(env.PioPlatform().get_dir()),
          'platform_version':env.PioPlatform().version,'cppdefines':env.get('CPPDEFINES',[]),
          'build_flags':env.get('BUILD_FLAGS',[]),'application':resolved('$BUILD_DIR/${PROGNAME}.bin'),
          'application_offset':resolved(env.get('ESP32_APP_OFFSET','UNAVAILABLE')),
          'extra_images':[{'offset':resolved(offset),'file':resolved(path)} for offset,path in env.get('FLASH_EXTRA_IMAGES',[])],
          'uploadcmd_template':str(env.get('UPLOADCMD','')),'flash_performed':False}
    Path(resolved('$BUILD_DIR/flash_layout.json')).write_text(json.dumps(data,indent=2,default=str)+'\n',encoding='utf-8')
env.AddPostAction('$BUILD_DIR/${PROGNAME}.bin',emit)
