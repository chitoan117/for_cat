// Optional post-review panel for the existing for_cat app. Not deployed/mounted.
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:feeder_demo/live_camera_panel.dart';
import 'package:feeder_demo/ui_widgets.dart';

Map<String,dynamic> obj(Object? v)=>v is Map<String,dynamic>?v:<String,dynamic>{};
num? finiteNumber(Object? v)=>v is num && v.isFinite?v:null;
class HardwareDiagnosticsController extends ChangeNotifier {
  final Uri base,origin;
  final http.Client client;
  Map<String,dynamic>? data;
  Map<String,dynamic>? receipt;
  List<dynamic> events=[];
  String? exportedLog;
  String? error;
  Timer? _timer;
  bool _disposed=false,_busy=false,buzzerBusy=false;
  String? _pendingId;
  int _sequence=0;
  HardwareDiagnosticsController({required this.base,Uri? origin,http.Client? client})
    :origin=origin??Uri.base,client=client??http.Client();
  bool get sameOrigin=>base.origin==origin.origin && base.userInfo.isEmpty &&
    (base.scheme=='https' || base.scheme=='http' && ['localhost','127.0.0.1','::1'].contains(base.host));
  Future<void> start()async{await refresh();if(!_disposed)_timer=Timer.periodic(const Duration(seconds:1),(_)=>unawaited(refresh()));}
  Future<void> refresh()async{
    if(_disposed||_busy)return;
    if(!sameOrigin){data=null;error='Cần cùng origin HTTPS';notifyListeners();return;}
    _busy=true;
    try{
      final r=await client.get(base.resolve('/api/v1/hardware-diagnostics/status')).timeout(const Duration(seconds:3));
      if(_disposed)return;
      if(r.statusCode==404)throw const FormatException('DIAGNOSTIC_EXTENSION_NOT_DEPLOYED');
      if(r.statusCode!=200)throw FormatException('HTTP ${r.statusCode}');
      final next=obj(jsonDecode(r.body));
      if(next['schema_version']!='hardware_diagnostics_v1' ||
        !['REAL','SIMULATED','UNKNOWN'].contains(next['source']) ||
        next['simulated']!=(next['source']=='SIMULATED') || next['actuator_execution']!=false ||
        next['servo']!='LOCKED' || next['pump']!='LOCKED')throw const FormatException('Unsafe diagnostic contract');
      final ai=obj(next['ai']);
      if(!['CAT','DOG','NONE','UNKNOWN'].contains(ai['classification']) ||
        next['source']=='REAL'&&(ai['simulated']==true||['MOCK','SIMULATED'].contains(ai['data_source'])))throw const FormatException('AI source/class mismatch');
      data=next;error=null;
    }catch(e){if(!_disposed){data=null;error=e.toString();}}
    finally{_busy=false;if(!_disposed)notifyListeners();}
  }
  bool get connected=>obj(data?['connection'])['connected']==true&&obj(data?['connection'])['health']=='ESP32_CONNECTED';
  bool get canRecord=>sameOrigin&&obj(data?['permissions'])['CONTROL_SYSTEM']==true;
  bool get canTestBuzzer=>canRecord&&connected&&data?['source']=='REAL'&&obj(data?['buzzer'])['available']==true&&!buzzerBusy;
  Future<void> refreshEvents()async{
    if(_disposed||!sameOrigin)return;
    try{
      final r=await client.get(base.resolve('/api/v1/hardware-diagnostics/events')).timeout(const Duration(seconds:3));
      if(_disposed)return;
      final value=jsonDecode(r.body);if(r.statusCode!=200||value is! List||value.length>50)throw const FormatException('Diagnostic log unavailable');
      events=value;error=null;
    }catch(e){if(!_disposed){events=[];error=e.toString();}}
    if(!_disposed)notifyListeners();
  }
  Future<void> recordObservation(String note)async{
    if(_disposed||!canRecord||note.isEmpty||note.length>1024)return;
    try{
      final r=await client.post(base.resolve('/api/v1/hardware-diagnostics/observations'),headers:{'Content-Type':'application/json'},
        body:jsonEncode({'sensor_id':'SYSTEM','USER_OBSERVED':note})).timeout(const Duration(seconds:3));
      if(_disposed)return;
      if(r.statusCode!=200)throw const FormatException('Observation not recorded');
      await refreshEvents();
    }catch(e){if(!_disposed){error=e.toString();notifyListeners();}}
  }
  Future<void> exportEvents()async{
    if(_disposed||!sameOrigin)return;
    exportedLog=null;
    try{
      final r=await client.get(base.resolve('/api/v1/hardware-diagnostics/events/export')).timeout(const Duration(seconds:3));
      if(_disposed)return;
      final value=obj(jsonDecode(r.body));
      if(r.statusCode!=200||value['kind']!='BOUNDED_HARDWARE_TEST_LOG_EXPORT'||value['physical_pass']!=false)throw const FormatException('Invalid export');
      exportedLog=const JsonEncoder.withIndent('  ').convert(value);error=null;
    }catch(e){if(!_disposed){exportedLog=null;error=e.toString();}}
    if(!_disposed)notifyListeners();
  }
  Future<void> testBuzzer({required bool ownerConfirmed})async{
    if(!ownerConfirmed||!canTestBuzzer)return;
    buzzerBusy=true;_pendingId??='hwtest_${DateTime.now().millisecondsSinceEpoch}_${++_sequence}';notifyListeners();
    try{
      final r=await client.post(base.resolve('/api/v1/hardware-diagnostics/buzzer-test'),headers:{'Content-Type':'application/json'},
        body:jsonEncode({'request_id':_pendingId,'confirm':'BUZZER_GPIO2_ACTIVE_LOW_3V3_REVIEWED'})).timeout(const Duration(seconds:3));
      if(_disposed)return;
      if(r.statusCode!=200)throw FormatException('HTTP ${r.statusCode}: buzzer test không được phép');
      final next=obj(jsonDecode(r.body));
      if(next['request_id']!=_pendingId || next['status']!='REQUEST_RECEIVED_NOT_ACOUSTIC_PASS' || next['feed_success']!=false || next['physical_result']!='NOT_VERIFIED')throw const FormatException('Invalid buzzer receipt');
      receipt=next;_pendingId=null;error=null;
    }catch(e){if(!_disposed)error=e.toString();}
    finally{buzzerBusy=false;if(!_disposed)notifyListeners();}
  }
  @override void dispose(){_disposed=true;_timer?.cancel();client.close();super.dispose();}
}

class HardwareDiagnosticsPanel extends StatefulWidget {
  final HardwareDiagnosticsController controller;
  final bool showCamera;
  const HardwareDiagnosticsPanel({super.key,required this.controller,this.showCamera=true});
  @override State<HardwareDiagnosticsPanel> createState()=>_HardwareDiagnosticsPanelState();
}
class _HardwareDiagnosticsPanelState extends State<HardwareDiagnosticsPanel>{
  @override void initState(){super.initState();widget.controller.addListener(changed);unawaited(widget.controller.start());}
  void changed(){if(mounted)setState((){});}
  @override void dispose(){widget.controller.removeListener(changed);widget.controller.dispose();super.dispose();}
  @override Widget build(BuildContext context){
    final c=widget.controller,d=c.data;
    final source=d?['source']??'UNKNOWN',ai=obj(d?['ai']),pir=obj(d?['pir']),hx=obj(d?['hx711']);
    return AppCard(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      const Text('Nghiệm thu phần cứng — không điều khiển servo/pump'),
      Text('Nguồn: $source${source=='SIMULATED'?' · SIMULATED':''}'),
      if(d?['execution_context']=='OFFLINE_TEST_ONLY')const Text('TEST/MOCK — dữ liệu kiểm thử, không phải nghiệm thu thật'),
      Text('Kết nối: ${obj(d?['connection'])['health']??'UNKNOWN'}'),
      Text('Telemetry age: ${finiteNumber(obj(d?['telemetry_time'])['age_ms'])??'UNKNOWN'} ms · HOST_MONOTONIC_MS'),
      if(c.error!=null)Text(c.error!),
      Text('AI: ${ai['health']=='ONLINE'?ai['classification']??'UNKNOWN':'UNKNOWN'}'),
      Text('FOOD_ROI: ${obj(d?['FOOD_ROI'])['mode']??'UNKNOWN'} · config không phải frame membership proof'),
      if(widget.showCamera)LiveCameraPanel(isMock:false,base:c.base),
      for(final id in ['HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'])Builder(builder:(context){
        final s=obj(obj(d?['ultrasonic'])[id]);
        final cm=c.connected&&s['valid']==true?finiteNumber(s['distance_cm']):null;
        final level=obj(s['water_level']);final percent=cm!=null?finiteNumber(level['percent']):null;
        return Text('$id [${s['state']??'UNKNOWN'}]: ${cm??'null'} cm${id=='JSN_SR04T_1'?' · nước ${percent??'null'}% (${level['state']??'NOT_CONFIGURED'})':id=='JSN_SR04T_2'?' · role TBD':''}');
      }),
      Text('PIR: ${c.connected&&pir['valid']==true?(pir['motion']==true?'motion':'no-motion'):'UNKNOWN'} · ${pir['quality']??'UNKNOWN'}'),
      Text('HX711: ${c.connected?finiteNumber(hx['grams'])??'null':'null'} g · ${hx['authority']??'UNKNOWN'}'),
      const Text('HX711 static: PASS đã chấp nhận; persistence/closed-loop chưa xác minh'),
      Text('OLED: ${obj(d?['oled'])['health']??'UNKNOWN'} · dùng evidence hiển thị trước'),
      Text('Button GPIO21: ${c.connected?obj(d?['button'])['pressed']??'UNKNOWN':'UNKNOWN'} · count ${obj(d?['button'])['request_count']??'null'} · actuator BLOCKED'),
      Text('Buzzer: ${obj(d?['buzzer'])['reason']??'manual capability required'}'),
      ElevatedButton(onPressed:c.canTestBuzzer?()async{
        final yes=await showDialog<bool>(context:context,builder:(context)=>AlertDialog(
          title:const Text('Xác nhận bài buzzer riêng'),
          content:const Text('Chỉ GPIO2 ACTIVE_LOW 3.3V, OFF và firmware auto-off đã được review. ACK không phải đã nghe âm. Thử 2 tiếng ngắn?'),
          actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('Hủy')),
            TextButton(onPressed:()=>Navigator.pop(context,true),child:const Text('Tôi đã kiểm tra'))]));
        if(yes==true)await c.testBuzzer(ownerConfirmed:true);
      }:null,child:const Text('Thử buzzer an toàn')),
      if(c.receipt!=null)Text('Buzzer: ${c.receipt!['status']}'),
      TextButton(onPressed:()=>c.refreshEvents(),child:const Text('Xem nhật ký kiểm thử')),
      TextButton(onPressed:()async{
        await c.exportEvents();if(!context.mounted||c.exportedLog==null)return;
        await showDialog<void>(context:context,builder:(context)=>AlertDialog(title:const Text('Xuất log JSON — copy/lưu evidence'),content:SingleChildScrollView(child:SelectableText(c.exportedLog!))));
      },child:const Text('Xuất log JSON')),
      TextButton(onPressed:c.canRecord?()async{
        final input=TextEditingController();
        final note=await showDialog<String>(context:context,builder:(context)=>AlertDialog(
          title:const Text('USER_OBSERVED — không tự nghiệm thu PASS'),
          content:TextField(controller:input,maxLength:1024),
          actions:[TextButton(onPressed:()=>Navigator.pop(context,input.text),child:const Text('Ghi log'))]));
        input.dispose();if(note!=null)await c.recordObservation(note);
      }:null,child:const Text('Ghi nhận quan sát')),
      for(final item in c.events.take(5))Text('${obj(item)['kind']}: ${obj(item)['USER_OBSERVED']??obj(item)['physical_result']}'),
      const Text('Servo LOCKED · Pump LOCKED · Không suy PHYSICAL PASS từ telemetry/ACK'),
    ]));
  }
}
