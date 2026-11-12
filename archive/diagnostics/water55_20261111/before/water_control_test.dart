import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:feeder_demo/water_control_panel.dart';
import 'real_backend_test.dart' show backend;

Map<String,dynamic> off()=>{'fresh':true,'supported':true,'enabled':false,'running':false,'fault':false,'can_enable':true,'request':null};
void main(){
  testWidgets('confirmation is required, cancel does not post, queued is not enabled',(tester)async{
    final posts=<Map<String,dynamic>>[];
    final b=backend(MockClient((r)async{
      if(r.method=='POST'){posts.add(jsonDecode(r.body) as Map<String,dynamic>);return http.Response('{"queued":true,"applied":false}',202);}
      return http.Response(jsonEncode(off()),200);
    }));addTearDown(b.dispose);b.waterControl=off();
    await tester.pumpWidget(MaterialApp(home:Scaffold(body:WaterControlPanel(backend:b))));
    await tester.tap(find.text('Bật chức năng nước'));await tester.pumpAndSettle();
    expect(find.text('Bật chức năng nước?'),findsOneWidget);expect(posts,isEmpty);
    await tester.tap(find.text('Hủy'));await tester.pumpAndSettle();expect(posts,isEmpty);
    await tester.tap(find.text('Bật chức năng nước'));await tester.pumpAndSettle();
    await tester.tap(find.text('Xác nhận bật'));await tester.pumpAndSettle();
    expect(posts.single['action'],'ENABLE');expect(posts.single['confirmed'],isTrue);
    expect(find.text('Đang tắt'),findsAtLeastNWidgets(1));expect(find.text('Đang theo dõi mức nước'),findsNothing);
  });
  testWidgets('stop posts without confirmation; 320px layout fits',(tester)async{
    tester.view.physicalSize=const Size(320,800);tester.view.devicePixelRatio=1;addTearDown(tester.view.reset);
    final actions=<String>[];
    final b=backend(MockClient((r)async{
      if(r.method=='POST'){actions.add((jsonDecode(r.body) as Map)['action'] as String);return http.Response('{"queued":true}',202);}
      return http.Response(jsonEncode(off()),200);
    }));addTearDown(b.dispose);b.waterControl=off();
    await tester.pumpWidget(MaterialApp(home:Scaffold(body:WaterControlPanel(backend:b))));
    await tester.tap(find.text('Tắt bơm'));await tester.pumpAndSettle();expect(actions,['DISABLE']);expect(tester.takeException(),isNull);
  });
  test('unconfirmed programmatic enable never posts, stale is unknown',( )async{
    var posts=0;
    final b=backend(MockClient((r)async{if(r.method=='POST')posts++;return http.Response('{}',503);}));addTearDown(b.dispose);
    b.waterControl=off();await b.setWaterEnabled(true);expect(posts,0);
    await b.refreshWater();expect(b.waterControl,isNull);
  });
}
