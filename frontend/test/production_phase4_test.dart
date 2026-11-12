import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:feeder_demo/feeder_state.dart';
import 'package:feeder_demo/history_model.dart';
import 'package:feeder_demo/live_camera_controller.dart';
import 'package:feeder_demo/status_model.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'state_fixture.dart';

Map<String, dynamic> camera({String source='SIMULATED',String epoch='A'}) => {
  'status':'CAMERA_ONLINE','source':source,'simulated':source=='SIMULATED',
  'actuator_execution':false,'width':640,'height':480,'frame_age_seconds':.1,
  'annotations':'BURNED_IN_SAME_FRAME_NOT_STATUS_OVERLAY','producer_epoch':epoch,
  'stream_lease_seconds':300,
};
LiveCameraController controller(http.Client client) => LiveCameraController(
  base:Uri.parse('https://for-cat.tailtest.ts.net'),
  origin:Uri.parse('https://for-cat.tailtest.ts.net/flutter/'),client:client,
  pollInterval:const Duration(hours:1));

void main(){
  test('non-loopback same-origin camera still requires HTTPS',()async{
    var requests=0;
    final c=LiveCameraController(base:Uri.parse('http://for-cat.tailtest.ts.net'),
      origin:Uri.parse('http://for-cat.tailtest.ts.net/flutter/'),
      client:MockClient((_)async{requests++;return http.Response(jsonEncode(camera()),200);}));
    addTearDown(c.dispose);await c.start();
    expect(c.phase,CameraPhase.error);expect(requests,0);
  });
  test('producer/source transition cannot relabel decoded simulated JPEG as REAL',() async {
    var status=camera();final c=controller(MockClient((_) async=>http.Response(jsonEncode(status),200)));
    addTearDown(c.dispose);await c.start();c.firstFrame(c.generation);
    expect(c.phase,CameraPhase.live);final old=c.generation;
    status=camera(source:'REAL',epoch:'B');await c.refresh();
    expect(c.phase,CameraPhase.connecting);expect(c.decoded,isFalse);expect(c.generation,greaterThan(old));
    c.firstFrame(old);expect(c.phase,CameraPhase.connecting);
    c.streamError(old);expect(c.phase,CameraPhase.connecting);
    c.firstFrame(c.generation);expect(c.phase,CameraPhase.live);expect(c.simulated,isFalse);
  });
  test('epoch restart with same REAL source requires a new decoded image',() async {
    var status=camera(source:'REAL');final c=controller(MockClient((_)async=>http.Response(jsonEncode(status),200)));
    addTearDown(c.dispose);await c.start();c.firstFrame();final old=c.generation;
    status=camera(source:'REAL',epoch:'restarted');await c.refresh();
    expect(c.generation,greaterThan(old));expect(c.phase,CameraPhase.connecting);
  });
  test('stop/start ignores late status from previous viewing intent',() async {
    final old=Completer<http.Response>();var calls=0;
    final c=controller(MockClient((_)async {calls++;return calls==1?old.future:http.Response(jsonEncode(camera(source:'REAL',epoch:'new')),200);}));
    addTearDown(c.dispose);final first=c.start();c.stop();await c.start();
    final generation=c.generation;old.complete(http.Response(jsonEncode(camera()),200));await first;
    expect(c.simulated,isFalse);expect(c.generation,generation);expect(c.phase,CameraPhase.connecting);
  });
  test('permission/session loss clears LIVE and recovery decodes afresh',() async {
    var code=200;final c=controller(MockClient((_)async=>http.Response(jsonEncode(camera(source:'REAL')),code)));
    addTearDown(c.dispose);await c.start();c.firstFrame();expect(c.phase,CameraPhase.live);
    code=401;await c.refresh();expect(c.phase,CameraPhase.error);expect(c.decoded,isFalse);
    code=200;await c.refresh();expect(c.phase,CameraPhase.connecting);
    c.stop();expect(c.phase,CameraPhase.off);
  });
  test('REAL state rejects nested simulated AI and NONE never has confidence',(){
    final raw=fixture();raw['ai']={...(raw['ai'] as Map<String,dynamic>),'data_source':'SIMULATED','simulated':true};
    expect(()=>FeederState.decode(jsonEncode(raw)),throwsFormatException);
    raw['data_source']='MOCK';expect(FeederState.decode(jsonEncode(raw),allowMock:true).source,'MOCK');
    raw['data_source']='REAL';raw['ai']={'classification':'NONE','health':'ONLINE','confidence':.9};
    expect(FeederState.decode(jsonEncode(raw)).confidence,isNull);
  });
  test('gross/food delta cannot become actual dispensed without feed execution',(){
    final raw=fixture();(raw['weight'] as Map)['gross_measurement']=130;
    (raw['weight'] as Map)['food_delta']=35;
    expect(FeederState.decode(jsonEncode(raw)).actualDispensedGrams,isNull);
  });

  const path=String.fromEnvironment('FORCAT_PHASE4_FIXTURE');
  group('actual FastAPI exported contract',(){
    late Map<String,dynamic> exported;
    setUpAll((){exported=jsonDecode(File(path).readAsStringSync()) as Map<String,dynamic>;
      expect(exported['physical_pass'],isFalse);});
    test('CAT DOG NONE STALE provenance and timestamps parse in Flutter',(){
      final states=exported['states'] as Map<String,dynamic>;
      for(final species in ['CAT','DOG','NONE']){
        final state=FeederState.decode(jsonEncode(states[species]));
        expect(state.classification,species);expect(state.ai['data_source'],'REAL');
        expect(state.ai['source_frame_id'],isA<int>());expect(state.ai['age_seconds'],0);
        expect(state.grams,isNull);expect(state.actualDispensedGrams,isNull);
      }
      expect(FeederState.decode(jsonEncode(states['STALE'])).classification,'UNKNOWN');
    });
    test('request received remains pending, never success/history completion',(){
      final receipt=PreviewReceipt.decode(jsonEncode(exported['pending_receipt']),'phase4_received','APP');
      expect(receipt.complete,isFalse);expect(receipt.request['actual_dispensed_grams'],isNull);
      expect(HistoryEntry.fromReceipt(receipt)?.status.code,isNot('SUCCESS'));
    });
    test('camera API REAL/SIMULATED/status fields match controller',()async{
      var status=(exported['camera'] as Map)['REAL'];
      final c=controller(MockClient((_)async=>http.Response(jsonEncode(status),200)));addTearDown(c.dispose);
      await c.start();expect(c.phase,CameraPhase.connecting);expect(c.simulated,isFalse);
      c.firstFrame(c.generation);status=(exported['camera'] as Map)['SIMULATED'];await c.refresh();
      expect(c.phase,CameraPhase.connecting);expect(c.simulated,isTrue);
      status=(exported['camera'] as Map)['OFFLINE'];await c.refresh();expect(c.phase,CameraPhase.offline);
    });
  },skip:path.isEmpty?'Supply FORCAT_PHASE4_FIXTURE exported by focused FastAPI test':false);
}
