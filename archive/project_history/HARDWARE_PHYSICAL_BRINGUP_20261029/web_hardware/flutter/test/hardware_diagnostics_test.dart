import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import '../hardware_diagnostics_panel.dart';

Map<String,dynamic> fixture({bool simulated=false,bool buzzer=false})=>{
  'schema_version':'hardware_diagnostics_v1','source':simulated?'SIMULATED':'REAL','simulated':simulated,
  'execution_context':'OFFLINE_TEST_ONLY',
  'actuator_execution':false,'servo':'LOCKED','pump':'LOCKED','permissions':{'CONTROL_SYSTEM':true},
  'connection':{'connected':true,'health':'ESP32_CONNECTED'},
  'ai':{'classification':'DOG','health':'ONLINE','simulated':simulated,'data_source':simulated?'SIMULATED':'REAL'},
  'FOOD_ROI':{'mode':'FULL_FRAME'},'buzzer':{'available':buzzer,'reason':buzzer?null:'FIRMWARE_CAPABILITY_MISSING'},
  'ultrasonic':{for(final id in ['HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'])id:{
    'valid':true,'distance_cm':50,'water_level':id=='JSN_SR04T_1'?{'percent':75,'state':'CONFIGURED_GEOMETRY_ONLY'}:{'percent':null,'state':'NOT_CONFIGURED'}}},
  'pir':{'valid':false,'motion':null,'quality':'QUALIFIED_FIELDS_UNAVAILABLE_OR_STALE'},
  'hx711':{'grams':null,'authority':'NO_CURRENT_CALIBRATED_MEASUREMENT'},
};
HardwareDiagnosticsController make(http.Client client)=>HardwareDiagnosticsController(
  base:Uri.parse('https://forcat.test.ts.net'),origin:Uri.parse('https://forcat.test.ts.net/flutter/'),client:client);
void main(){
  testWidgets('reuse diagnostics labels, null geometry and unsupported buzzer are honest',(tester)async{
    final c=make(MockClient((_)async=>http.Response(jsonEncode(fixture()),200)));
    await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:HardwareDiagnosticsPanel(controller:c,showCamera:false)))));
    await tester.pump();await tester.pump();
    expect(find.textContaining('HC_SR04_1 [UNKNOWN]: 50 cm'),findsOneWidget);
    expect(find.textContaining('nước 75%'),findsOneWidget);
    expect(find.textContaining('JSN_SR04T_2 [UNKNOWN]: 50 cm · role TBD'),findsOneWidget);
    expect(find.textContaining('TEST/MOCK'),findsOneWidget);
    expect(find.textContaining('PIR: UNKNOWN'),findsOneWidget);
    expect(find.textContaining('HX711: null g'),findsOneWidget);
    final button=tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton,'Thử buzzer an toàn'));
    expect(button.onPressed,isNull);
    expect(find.textContaining('FOOD_ROI:'),findsOneWidget);expect(find.textContaining('WATER_ROI'),findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
  test('SIMULATED can never authorize real buzzer from an available flag',()async{
    var posts=0;final c=make(MockClient((r)async{if(r.method=='POST')posts++;return http.Response(jsonEncode(fixture(simulated:true,buzzer:true)),200);}));
    addTearDown(c.dispose);await c.refresh();await c.testBuzzer(ownerConfirmed:true);
    expect(c.canTestBuzzer,isFalse);expect(posts,0);
  });
  test('HTTP/source failures clear readings instead of retaining stale values',()async{
    var code=200;var value=fixture();final c=make(MockClient((_)async=>http.Response(jsonEncode(value),code)));
    addTearDown(c.dispose);await c.refresh();expect(c.data,isNotNull);
    code=503;await c.refresh();expect(c.data,isNull);
    code=200;value=fixture();value['pump']='ARMED';await c.refresh();expect(c.data,isNull);
  });
  test('missing extension404 does not invent an existing hardware API',()async{
    final c=make(MockClient((_)async=>http.Response('{}',404)));addTearDown(c.dispose);
    await c.refresh();expect(c.data,isNull);expect(c.error,contains('NOT_DEPLOYED'));
  });
  test('fixed buzzer request requires explicit confirmation and is receipt only',()async{
    var posts=0;final c=make(MockClient((r)async{
      if(r.method=='GET')return http.Response(jsonEncode(fixture(buzzer:true)),200);
      posts++;final body=jsonDecode(r.body) as Map<String,dynamic>;
      expect(body.keys.toSet(),{'request_id','confirm'});
      return http.Response(jsonEncode({'request_id':body['request_id'],'status':'REQUEST_RECEIVED_NOT_ACOUSTIC_PASS','feed_success':false,'physical_result':'NOT_VERIFIED'}),200);
    }));addTearDown(c.dispose);await c.refresh();
    await c.testBuzzer(ownerConfirmed:false);expect(posts,0);
    await c.testBuzzer(ownerConfirmed:true);expect(posts,1);expect(c.receipt?['feed_success'],isFalse);
  });
  test('observer log is explicit, bounded data not an actuator command',()async{
    var observations=0;final c=make(MockClient((r)async{
      if(r.url.path.endsWith('/status'))return http.Response(jsonEncode(fixture()),200);
      if(r.method=='POST'){observations++;expect(jsonDecode(r.body)['USER_OBSERVED'],'HC1 target40cm');return http.Response('{"recorded":true}',200);}
      return http.Response('[{"kind":"USER_OBSERVED","USER_OBSERVED":"HC1 target40cm","physical_result":"NOT_VERIFIED"}]',200);
    }));addTearDown(c.dispose);await c.refresh();await c.recordObservation('HC1 target40cm');
    expect(observations,1);expect(c.events.length,1);
  });
  test('remote HTTP or cross-origin must not request diagnostics',()async{
    var requests=0;final c=HardwareDiagnosticsController(base:Uri.parse('http://forcat.test.ts.net'),origin:Uri.parse('http://forcat.test.ts.net/flutter/'),
      client:MockClient((_)async{requests++;return http.Response('{}',200);}));addTearDown(c.dispose);
    await c.refresh();expect(requests,0);expect(c.data,isNull);
  });
  test('log export remains data-only and never posts a hardware command',()async{
    var posts=0;final c=make(MockClient((r)async{
      if(r.method=='POST')posts++;
      return http.Response('{"kind":"BOUNDED_HARDWARE_TEST_LOG_EXPORT","physical_pass":false,"events":[]}',200);
    }));addTearDown(c.dispose);await c.exportEvents();
    expect(c.exportedLog,contains('BOUNDED_HARDWARE_TEST_LOG_EXPORT'));expect(posts,0);
  });
}
