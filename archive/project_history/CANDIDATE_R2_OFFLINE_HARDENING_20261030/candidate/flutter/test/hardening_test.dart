import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:feeder_demo/live_camera_panel.dart';
import '../hardware_diagnostics_panel.dart';
import '../offline_history_panel.dart';
import 'baseline_panel.dart' as baseline;
Map<String,dynamic> load(String name)=>jsonDecode(File('${Platform.environment['HARDENING_OUTPUT']}/$name.json').readAsStringSync()) as Map<String,dynamic>;
Map<String,dynamic> frame(String name)=>Map<String,dynamic>.from((load('e2e_api')['cases'] as Map)[name] as Map);
HardwareDiagnosticsController controller(http.Client c,{int Function()? clock})=>HardwareDiagnosticsController(
  base:Uri.parse('https://forcat.test.ts.net'),origin:Uri.parse('https://forcat.test.ts.net/flutter/'),client:c,monotonicMillis:clock);
void main(){
  testWidgets('baseline static cache stays connected but fixed cache expires',(tester)async{
    final body=jsonEncode(frame('healthy_cat'));
    final old=baseline.HardwareDiagnosticsController(base:Uri.parse('https://forcat.test.ts.net'),origin:Uri.parse('https://forcat.test.ts.net/flutter/'),client:MockClient((_)async=>http.Response(body,200)));
    var now=0;final fixed=controller(MockClient((_)async=>http.Response(body,200)),clock:()=>now);
    await old.refresh();await fixed.refresh();await tester.pump(const Duration(seconds:4));now=4000;
    expect(old.connected,isTrue);expect(fixed.connected,isFalse);
    debugPrint('BASELINE_CONNECTED_AFTER_4S=true FIXED_CONNECTED_AFTER_4S=false source=SIMULATED');
    old.dispose();fixed.dispose();
  });
  for(final name in ['healthy_cat','progress_dog','recovered_none','ai_unknown','out_of_order','timeout','disconnect','wrong_host_boot','unsafe_still_latched']){
    testWidgets('connected E2E fixture $name reaches dashboard honestly',(tester)async{
      final c=controller(MockClient((_)async=>http.Response(jsonEncode(frame(name)),200)),clock:()=>0);
      await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:HardwareDiagnosticsPanel(controller:c,showCamera:false)))));
      await tester.pump();await tester.pump();
      expect(find.textContaining('TEST/MOCK'),findsOneWidget);
      expect(find.textContaining('±5 g'),findsOneWidget);
      if(name=='healthy_cat'){
        expect(find.textContaining('HX711: 34.981 g'),findsOneWidget);expect(find.text('AI: CAT'),findsOneWidget);
      }else if(name=='progress_dog'){expect(find.text('AI: DOG'),findsOneWidget);}
      else if(name=='recovered_none'){expect(find.text('AI: NONE'),findsOneWidget);}
      else if(name=='ai_unknown'){expect(find.text('AI: UNKNOWN'),findsOneWidget);}
      else{expect(find.textContaining('HC_SR04_1 ['),findsOneWidget);expect(find.textContaining('HX711: null g'),findsOneWidget);}
      await tester.pumpWidget(const SizedBox());
    });
  }
  test('identical replay cannot reset local freshness or AI age',()async{
    var now=0;final c=controller(MockClient((_)async=>http.Response(jsonEncode(frame('healthy_cat')),200)),clock:()=>now);
    addTearDown(c.dispose);await c.refresh();expect(c.connected,isTrue);
    now=2500;await c.refresh();expect(c.sensorState(Map<String,dynamic>.from((c.data!['ultrasonic'] as Map)['HC_SR04_1'] as Map)),'STALE');
    expect(c.aiClassification,'UNKNOWN');now=3500;await c.refresh();expect(c.connected,isFalse);expect(c.connectionHealth,'ESP32_STALE');
  });
  test('HTTP pending/unavailable and delayed response never refresh stale values',()async{
    var now=0;var blocked=false;final pending=Completer<http.Response>();
    final c=controller(MockClient((_)=>blocked?pending.future:Future.value(http.Response(jsonEncode(frame('healthy_cat')),200))),clock:()=>now);
    addTearDown(c.dispose);await c.refresh();blocked=true;final next=c.refresh();now=4000;
    expect(c.connected,isFalse);pending.complete(http.Response('{}',503));await next;expect(c.data,isNull);
    final delayed=Completer<http.Response>();now=0;
    final d=controller(MockClient((_)=>delayed.future),clock:()=>now);addTearDown(d.dispose);
    final request=d.refresh();now=3500;delayed.complete(http.Response(jsonEncode(frame('healthy_cat')),200));await request;expect(d.connected,isFalse);
  });
  test('fake LIVE and old tolerance payloads rejected',()async{
    for(final bad in ['LIVE','OLD_POLICY','ZERO_DISTANCE']){
      final value=frame('healthy_cat');
      if(bad=='LIVE'){value['source']='REAL';value['simulated']=false;}
      if(bad=='OLD_POLICY'){value['feeding_mass_policy']={'target_grams':35,'tolerance_grams':.2};}
      if(bad=='ZERO_DISTANCE'){((value['ultrasonic'] as Map)['HC_SR04_1'] as Map)['distance_cm']=0;}
      final c=controller(MockClient((_)async=>http.Response(jsonEncode(value),200)),clock:()=>0);
      await c.refresh();expect(c.data,isNull);c.dispose();
    }
  });
  testWidgets('SIMULATED default camera slot never instantiates live camera',(tester)async{
    final c=controller(MockClient((_)async=>http.Response(jsonEncode(frame('healthy_cat')),200)),clock:()=>0);
    await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:HardwareDiagnosticsPanel(controller:c)))));
    await tester.pump();await tester.pump();expect(find.byType(LiveCameraPanel),findsNothing);
    expect(find.textContaining('live camera disabled'),findsOneWidget);await tester.pumpWidget(const SizedBox());
  });
  for(final grams in [29,30,35,36,38,40,41]){
    testWidgets('actual API mass$grams shown without coercing it to35',(tester)async{
      final data=load('mass_$grams'),ack=Map<String,dynamic>.from(load('mass_$grams')['ack'] as Map);
      final result=Map<String,dynamic>.from(data['final'] as Map);
      expect(feedLabel(ack),startsWith('PENDING'));
      await tester.pumpWidget(MaterialApp(home:Scaffold(body:FeedResultTile(result:result))));
      if(grams>=30&&grams<=40){
        expect(find.textContaining('COMPLETE'),findsOneWidget);expect(find.textContaining('Actual: $grams.0 g'),findsOneWidget);
      }else{expect(find.textContaining('FAULT'),findsOneWidget);}
      if(grams==41){expect(find.textContaining('Actual: null g'),findsOneWidget);expect(find.textContaining('Last observed: 41'),findsOneWidget);}
    });
  }
  test('mass pass alone and ACK never mean COMPLETE',(){
    expect(feedLabel({'state':'PENDING','mass_in_band':true,'final_status_received':false}),startsWith('PENDING'));
    expect(feedLabel({'state':'ERROR','mass_in_band':true,'final_status_received':true}),startsWith('FAULT'));
    expect(feedLabel({'state':'SUCCESS','mass_in_band':false,'final_status_received':true}),startsWith('FAULT'));
    expect(feedLabel({'state':'SUCCESS','mass_in_band':null,'final_status_received':true}),contains('MASS_UNKNOWN'));
  });
}
