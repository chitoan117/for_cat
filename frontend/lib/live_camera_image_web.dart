import 'dart:js_interop';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

Widget liveCameraImage(Uri uri, VoidCallback onFrame, VoidCallback onError) =>
    _CameraImage(uri: uri, onFrame: onFrame, onError: onError);

class _CameraImage extends StatefulWidget {
  final Uri uri;
  final VoidCallback onFrame, onError;
  const _CameraImage({
    required this.uri,
    required this.onFrame,
    required this.onError,
  });
  @override
  State<_CameraImage> createState() => _CameraImageState();
}

class _CameraImageState extends State<_CameraImage> {
  web.HTMLImageElement? _image;
  JSFunction? _loaded, _failed;
  Timer? _decodeCheck;
  @override
  Widget build(BuildContext context) => HtmlElementView.fromTagName(
    tagName: 'img',
    onElementCreated: (element) {
      final image = element as web.HTMLImageElement;
      _image = image;
      image.alt = 'CAMERA TRỰC TIẾP — chú thích AI gắn trong chính từng frame';
      image.style.width = '100%';
      image.style.height = '100%';
      image.style.objectFit = 'contain';
      _loaded = ((web.Event _) {
        if (mounted) widget.onFrame();
      }).toJS;
      _failed = ((web.Event _) {
        if (mounted) widget.onError();
      }).toJS;
      image.addEventListener('load', _loaded);
      image.addEventListener('error', _failed);
      image.src = widget.uri.toString();
      // Some browsers do not emit a conventional load event until an MJPEG
      // response ends. Natural dimensions confirm that a frame was decoded.
      _decodeCheck = Timer.periodic(const Duration(milliseconds: 250), (timer) {
        if (!mounted) {
          timer.cancel();
          return;
        }
        if (image.naturalWidth > 0 && image.naturalHeight > 0) {
          timer.cancel();
          widget.onFrame();
        }
      });
    },
  );
  @override
  void dispose() {
    _decodeCheck?.cancel();
    final image = _image;
    if (image != null) {
      image.removeEventListener('load', _loaded);
      image.removeEventListener('error', _failed);
      image.removeAttribute('src');
      image.remove();
    }
    super.dispose();
  }
}
