import 'package:flutter/material.dart';
import 'closed_loop_feed_panel.dart';

void main() => runApp(const MaterialApp(home: Scaffold(
  body: SafeArea(child: Padding(padding: EdgeInsets.all(16), child: Column(children: [
    Text('OFFLINE COMPONENT HARNESS — NOT CONNECTED TO HARDWARE'),
    ClosedLoopHistoryPanel(entries: []),
  ]))),
)));
