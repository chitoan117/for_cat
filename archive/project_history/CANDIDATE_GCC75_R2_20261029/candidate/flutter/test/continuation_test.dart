import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import '../hardware_diagnostics_panel.dart';
import '../offline_history_panel.dart';

Map<String,dynamic> load(String name)=>jsonDecode(File('${Platform.environment['FORCAT_R2_OUTPUT']}/fixtures/$name.json').readAsStringSync()) as Map<String,dynamic>;
HardwareDiagnosticsController controller(http.Client client)=>HardwareDiagnosticsController(
  base:Uri.parse('https://forcat.test.ts.net'),origin:Uri.parse('https://forcat.test.ts.net/flutter/'),client:client);
void main(){
  for(final name in ['healthy','stale','disconnected','invalid','timeout','duplicate_frozen','reconnect_waiting','unsafe_latched']){
    testWidgets('actual ASGI fixture $name renders provenance/nulls/states',(tester)async{
      final data=Map<String,dynamic>.from((load('api_contract')['cases'] as Map)[name] as Map);
      final c=controller(MockClient((_)async=>http.Response(jsonEncode(data),200)));
      await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:HardwareDiagnosticsPanel(controller:c,showCamera:false)))));
      await tester.pump();await tester.pump();
      expect(find.textContaining('TEST/MOCK'),findsOneWidget);
      expect(find.textContaining('Nguồn: SIMULATED'),findsOneWidget);
      expect(find.textContaining('JSN_SR04T_2'),findsOneWidget);
      expect(find.textContaining('WATER_ROI'),findsNothing);
      if(name=='healthy'){
        expect(find.textContaining('HC_SR04_1 [OK]'),findsOneWidget);
        expect(find.textContaining('HX711: 34.981 g'),findsOneWidget);
        expect(find.textContaining('PIR: motion'),findsOneWidget);
        expect(find.textContaining('OLED: HEALTHY'),findsOneWidget);
        expect(find.textContaining('count 1'),findsOneWidget);
      }else if(name=='timeout'){
        expect(find.textContaining('HC_SR04_2 [TIMEOUT]: null cm'),findsOneWidget);
      }else{
        final expected=name=='invalid'||name=='unsafe_latched'?'INVALID':name=='duplicate_frozen'||name=='reconnect_waiting'?'STALE':name.toUpperCase();
        expect(find.textContaining('HC_SR04_1 [$expected]: null cm'),findsOneWidget);
        expect(find.textContaining('HX711: null g'),findsOneWidget);
      }
      expect(tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton,'Thử buzzer an toàn')).onPressed,isNull);
      await tester.pumpWidget(const SizedBox());
    });
  }
  test('failed export invalidates last successful export regression',()async{
    var success=true;final c=controller(MockClient((_)async=>http.Response(success?'{"kind":"BOUNDED_HARDWARE_TEST_LOG_EXPORT","physical_pass":false,"events":[]}':'{}',success?200:503)));
    addTearDown(c.dispose);await c.exportEvents();expect(c.exportedLog,isNotNull);
    success=false;await c.exportEvents();expect(c.exportedLog,isNull);expect(c.error,isNotNull);
  });
  testWidgets('actual mock API ACK/history fixture never presents ACK as success',(tester)async{
    final fixture=load('feed_contract');
    expect(feedLabel(Map<String,dynamic>.from(fixture['ack'] as Map)),startsWith('PENDING'));
    expect(feedLabel(Map<String,dynamic>.from(fixture['after_disconnect'] as Map)),startsWith('PENDING'));
    await tester.pumpWidget(MaterialApp(home:Scaffold(body:OfflineHistoryPanel(fixture:fixture))));
    expect(find.textContaining('SIMULATION_SUCCESS'),findsOneWidget);
    expect(find.textContaining('PENDING — ACK'),findsNWidgets(2));
    expect(find.textContaining('Feeding records: 1'),findsOneWidget);
    expect(find.textContaining('Drinking records: 1'),findsOneWidget);
  });
  test('unknown/ACK states never map to SUCCESS',(){
    for(final state in ['ACK','REQUEST_RECEIVED','PENDING','ERROR','REJECTED','UNKNOWN',null]){
      expect(feedLabel({'state':state}),isNot(contains('SUCCESS')));
    }
  });
  test('timestamp/age and reason survive actual API contract mapping',()async{
    final data=Map<String,dynamic>.from((load('api_contract')['cases'] as Map)['stale'] as Map);
    final c=controller(MockClient((_)async=>http.Response(jsonEncode(data),200)));
    addTearDown(c.dispose);await c.refresh();
    expect((c.data?['telemetry_time'] as Map)['clock_domain'],'HOST_MONOTONIC_MS');
    expect((c.data?['telemetry_time'] as Map)['age_ms'],greaterThan(2000));
    expect(((c.data?['ultrasonic'] as Map)['HC_SR04_1'] as Map)['reason'],'STALE');
  });
  for(final scenario in ['nominal','lower_bound','upper_bound','over_band','overshoot_36','under_band','direct_launch_36','masked_window_36','timeout','stale_hx','invalid_hx','nonfinite_hx','disconnect','duplicate','duplicate_samples','journal_failure']){
    test('R2 actual API final status $scenario is not ACK success',(){
      final data=load('r2_feed_$scenario');
      expect(data['source'],'SIMULATED');expect(data['physical_pass'],isFalse);
      expect(feedLabel(Map<String,dynamic>.from(data['ack'] as Map)),startsWith('PENDING'));
      final state=(data['controller'] as Map)['state'];
      final label=feedLabel(Map<String,dynamic>.from(data['final'] as Map));
      if(state=='COMPLETE'){
        expect(label,startsWith('SIMULATION_SUCCESS'));
      }else{
        expect(label,'SIMULATION_ERROR');expect(label,isNot(contains('SUCCESS')));
      }
    });
  }
}
