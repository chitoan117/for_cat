// Offline fixture harness, not mounted in production. Uses actual API state names.
import 'package:flutter/material.dart';
import 'package:feeder_demo/ui_widgets.dart';

String feedLabel(Map<String,dynamic> result)=>switch(result['state']){
  'SUCCESS'=>result['final_status_received']==true&&result['mass_in_band']==true?'COMPLETE — SIMULATION_SUCCESS · final FEED_STATUS':result['mass_in_band']==false?'FAULT — MASS_OUTSIDE_BAND':'FINAL_STATUS — MASS_UNKNOWN',
  'PENDING'||'REQUEST_RECEIVED'=>'PENDING — ACK không xác nhận đã cấp thức ăn',
  'ERROR'||'REJECTED'=>'FAULT — SIMULATION_ERROR',
  _=>'UNKNOWN',
};
class FeedResultTile extends StatelessWidget{
  final Map<String,dynamic> result;
  const FeedResultTile({super.key,required this.result});
  @override Widget build(BuildContext context)=>Column(children:[
    Text(feedLabel(result)),
    Text('Measurement source: ${result['measurement_source']??'UNKNOWN'}'),
    Text('Actual: ${result['actual_dispensed_grams']??'null'} g · target 35 g ±5 g'),
    Text('Last observed: ${result['latest_observed_grams']??'null'} g'),
  ]);
}
class OfflineHistoryPanel extends StatelessWidget{
  final Map<String,dynamic> fixture;
  const OfflineHistoryPanel({super.key,required this.fixture});
  @override Widget build(BuildContext context){
    if(fixture['source']!='SIMULATED'||fixture['execution_context']!='OFFLINE_TEST_ONLY'||fixture['physical_pass']!=false){
      return const Text('INVALID OFFLINE FIXTURE');
    }
    return AppCard(child:Column(children:[
      const Text('TEST/MOCK — feeding/drinking history'),
      Text('ACK: ${feedLabel(Map<String,dynamic>.from(fixture['ack'] as Map))}'),
      Text('Disconnect: ${feedLabel(Map<String,dynamic>.from(fixture['after_disconnect'] as Map))}'),
      Text('Final: ${feedLabel(Map<String,dynamic>.from(fixture['final'] as Map))}'),
      FeedResultTile(result:Map<String,dynamic>.from(fixture['final'] as Map)),
      Text('Feeding records: ${(fixture['feeding_sessions'] as List).length}'),
      Text('Drinking records: ${(fixture['drinking_history'] as List).length} · MOCK, volume chưa xác minh'),
    ]));
  }
}
