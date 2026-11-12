// Offline fixture harness, not mounted in production. Uses actual API state names.
import 'package:flutter/material.dart';
import 'package:feeder_demo/ui_widgets.dart';

String feedLabel(Map<String,dynamic> result)=>switch(result['state']){
  'SUCCESS'=>'SIMULATION_SUCCESS — final FEED_STATUS',
  'PENDING'||'REQUEST_RECEIVED'=>'PENDING — ACK không xác nhận đã cấp thức ăn',
  'ERROR'||'REJECTED'=>'SIMULATION_ERROR',
  _=>'UNKNOWN',
};
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
      Text('Feeding records: ${(fixture['feeding_sessions'] as List).length}'),
      Text('Drinking records: ${(fixture['drinking_history'] as List).length} · MOCK, volume chưa xác minh'),
    ]));
  }
}
