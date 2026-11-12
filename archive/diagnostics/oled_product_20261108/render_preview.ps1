Add-Type -AssemblyName System.Drawing
$oledRoot = $PSScriptRoot
$oledCases = @(
  @('home','Sẵn sàng'), @('cat','Nhận diện mèo'), @('dog','Nhận diện chó'),
  @('feeding','Đang cấp thức ăn'), @('closing','Đang đóng cửa'),
  @('warning','Lượt trước chưa đủ'), @('sensors','Chi tiết cảm biến'),
  @('no_scale','Cần kiểm tra cân'), @('inspection','Cần kiểm tra cửa'),
  @('paused','Tạm dừng'), @('calibration','Hiệu chuẩn')
)
function Read-OledFrame([string]$frameName) {
  $tokens = (Get-Content -Raw -LiteralPath (Join-Path $oledRoot ($frameName+'.pgm'))).Trim() -split '\s+'
  if ($tokens[0] -ne 'P2') { throw 'Expected grayscale framebuffer' }
  $bitmap = [System.Drawing.Bitmap]::new(128,64)
  for ($y=0; $y -lt 64; $y++) {
    for ($x=0; $x -lt 128; $x++) {
      $color = if ($tokens[4+$y*128+$x] -eq '255') { [System.Drawing.Color]::White } else { [System.Drawing.Color]::Black }
      $bitmap.SetPixel($x,$y,$color)
    }
  }
  return $bitmap
}
function Write-OledSheet($cases, [int]$columns, [string]$fileName) {
  $scale=3; $gap=28; $heading=32; $tileWidth=384; $tileHeight=192
  $rows=[int][Math]::Ceiling($cases.Count/[double]$columns)
  $sheet=[System.Drawing.Bitmap]::new(($columns*($tileWidth+$gap)+$gap),($rows*($tileHeight+$heading+$gap)+$gap))
  $graphics=[System.Drawing.Graphics]::FromImage($sheet)
  $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml('#171b20'))
  $graphics.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
  $graphics.PixelOffsetMode=[System.Drawing.Drawing2D.PixelOffsetMode]::Half
  $font=[System.Drawing.Font]::new('Segoe UI',14)
  $pen=[System.Drawing.Pen]::new([System.Drawing.ColorTranslator]::FromHtml('#515861'))
  for ($i=0; $i -lt $cases.Count; $i++) {
    $x=$gap+($i%$columns)*($tileWidth+$gap)
    $y=$gap+[int][Math]::Floor($i/$columns)*($tileHeight+$heading+$gap)
    $graphics.DrawString($cases[$i][1],$font,[System.Drawing.Brushes]::White,[single]$x,[single]$y)
    $frame=Read-OledFrame $cases[$i][0]
    $graphics.DrawImage($frame,[System.Drawing.Rectangle]::new($x,($y+$heading),$tileWidth,$tileHeight),0,0,128,64,[System.Drawing.GraphicsUnit]::Pixel)
    $graphics.DrawRectangle($pen,($x-1),($y+$heading-1),($tileWidth+1),($tileHeight+1))
    $frame.Dispose()
  }
  $sheet.Save((Join-Path $oledRoot $fileName),[System.Drawing.Imaging.ImageFormat]::Png)
  $pen.Dispose();$font.Dispose();$graphics.Dispose();$sheet.Dispose()
}
Write-OledSheet $oledCases 2 'qa_all_states.png'
Write-OledSheet @($oledCases[1],$oledCases[3],$oledCases[6]) 3 'oled_preview.png'
Write-Output 'Rendered production OLED frames with actual classic5x7 font.'
