import 'dart:async';

import 'package:flutter/material.dart';

import 'live_camera_controller.dart';
import 'live_camera_image.dart';
import 'ui_widgets.dart';

typedef CameraImageBuilder = Widget Function(Uri, VoidCallback, VoidCallback);

class LiveCameraPanel extends StatefulWidget {
  final bool isMock;
  final Uri? base;
  final String mockClassification;
  final bool mockRoiEnabled;
  final LiveCameraController? controller;
  final CameraImageBuilder? imageBuilder;
  const LiveCameraPanel({
    super.key,
    required this.isMock,
    this.base,
    this.mockClassification = 'NONE',
    this.mockRoiEnabled = false,
    this.controller,
    this.imageBuilder,
  });
  @override
  State<LiveCameraPanel> createState() => _LiveCameraPanelState();
}

class _LiveCameraPanelState extends State<LiveCameraPanel>
    with AutomaticKeepAliveClientMixin {
  LiveCameraController? _controller;
  Timer? _mockTimer;
  bool _mockOn = false;
  int _frame = 0;
  @override
  bool get wantKeepAlive =>
      widget.isMock ? _mockOn : (_controller?.wanted ?? false);
  @override
  void initState() {
    super.initState();
    if (!widget.isMock) {
      _controller =
          widget.controller ??
          LiveCameraController(base: widget.base ?? Uri.base);
      _controller!.addListener(_changed);
    }
  }

  void _changed() {
    if (mounted) {
      updateKeepAlive();
      setState(() {});
    }
  }

  void _toggle() {
    if (widget.isMock) {
      setState(() => _mockOn = !_mockOn);
      updateKeepAlive();
      _mockTimer?.cancel();
      if (_mockOn) {
        _mockTimer = Timer.periodic(const Duration(milliseconds: 200), (_) {
          if (mounted) setState(() => _frame++);
        });
      }
    } else if (_controller!.wanted) {
      _controller!.stop();
    } else {
      unawaited(_controller!.start());
    }
  }

  @override
  void dispose() {
    _mockTimer?.cancel();
    _controller?.removeListener(_changed);
    if (widget.controller == null) {
      _controller?.dispose();
    } else {
      _controller?.stop();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final c = _controller;
    final wanted = widget.isMock ? _mockOn : c!.wanted;
    final phase = widget.isMock
        ? (_mockOn ? CameraPhase.live : CameraPhase.off)
        : c!.phase;
    final simulated = widget.isMock || (c?.simulated ?? false);
    final state = switch (phase) {
      CameraPhase.off => 'OFF',
      CameraPhase.connecting => 'CONNECTING',
      CameraPhase.live => 'LIVE',
      CameraPhase.offline => 'OFFLINE',
      CameraPhase.error => 'ERROR',
    };
    final render =
        !widget.isMock &&
        wanted &&
        (phase == CameraPhase.connecting || phase == CameraPhase.live) &&
        c!.generation > 0;
    final imageGeneration = c?.generation;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.videocam_outlined),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'CAMERA TRỰC TIẾP',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
              TextButton(
                onPressed: _toggle,
                child: Text(wanted ? 'Tắt camera' : 'Xem camera'),
              ),
            ],
          ),
          Text(
            '$state${simulated ? ' · SIMULATED' : ''}',
            key: const ValueKey('camera-phase'),
          ),
          if (wanted && widget.isMock)
            AspectRatio(
              aspectRatio: 4 / 3,
              child: CustomPaint(
                painter: _MockCameraPainter(
                  _frame,
                  widget.mockClassification,
                  widget.mockRoiEnabled,
                ),
              ),
            ),
          if (render)
            AspectRatio(
              aspectRatio: c.width / c.height,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  KeyedSubtree(
                    key: ValueKey('camera-${c.generation}'),
                    child: (widget.imageBuilder ?? liveCameraImage)(
                      c.streamUri,
                      () => c.firstFrame(imageGeneration),
                      () => c.streamError(imageGeneration),
                    ),
                  ),
                  if (phase == CameraPhase.connecting)
                    const IgnorePointer(
                      child: Center(child: CircularProgressIndicator()),
                    ),
                ],
              ),
            ),
          if (wanted && phase == CameraPhase.offline)
            const InfoNote(
              'CAMERA_OFFLINE — chưa có nguồn frame. Không có hình camera thật.',
            ),
          if (wanted && c?.error != null) InfoNote(c!.error!),
          if (wanted)
            const InfoNote(
              'CAT/DOG/NONE, độ tin cậy, bbox, ROI và timestamp được gắn trong chính frame; không dùng status cũ để vẽ overlay.',
            ),
          if (!wanted)
            const Text('Chỉ xem video; không phát sinh yêu cầu cho ăn.'),
        ],
      ),
    );
  }
}

class _MockCameraPainter extends CustomPainter {
  final int frame;
  final String classification;
  final bool roi;
  _MockCameraPainter(this.frame, this.classification, this.roi);
  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = const Color(0xff172b3b),
    );
    final type = ['CAT', 'DOG', 'NONE'].contains(classification)
        ? classification
        : 'NONE';
    if (type != 'NONE') {
      final dx = (frame % 10) * .005;
      canvas.drawRect(
        Rect.fromLTWH(
          size.width * (.2 + dx),
          size.height * .23,
          size.width * .5,
          size.height * .55,
        ),
        Paint()
          ..color = (type == 'CAT' ? Colors.greenAccent : Colors.redAccent)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3,
      );
    }
    if (roi) {
      canvas.drawRect(
        Rect.fromLTRB(
          size.width * .1,
          size.height * .2,
          size.width * .85,
          size.height * .95,
        ),
        Paint()
          ..color = Colors.yellow
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
    final text = TextPainter(
      text: TextSpan(
        text:
            'SIMULATED — KHÔNG PHẢI CAMERA THẬT\n$type · frame $frame · ${roi ? 'ROI_ENABLED' : 'FULL_FRAME'}',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          backgroundColor: Color(0xff7d1526),
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout(maxWidth: size.width - 16);
    text.paint(canvas, const Offset(8, 8));
  }

  @override
  bool shouldRepaint(covariant _MockCameraPainter oldDelegate) =>
      frame != oldDelegate.frame ||
      classification != oldDelegate.classification ||
      roi != oldDelegate.roi;
}
