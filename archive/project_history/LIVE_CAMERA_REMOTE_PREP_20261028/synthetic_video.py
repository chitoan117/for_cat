"""Explicit SYNTHETIC/SIMULATED frames; never imports cv2/opens a webcam."""
import asyncio
import io
import time
from PIL import Image, ImageDraw

def render_frame(frame_id, captured_ms, classification='CAT', roi_enabled=False, width=640, height=480):
    image=Image.new('RGB',(width,height),(17+(frame_id%30),35,52));draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,width-1,55),fill=(120,10,30))
    draw.text((10,9),'SIMULATED - NOT A REAL CAMERA',fill='white')
    draw.text((10,30),'%s | frame %s | capture-ms %s'%(classification,frame_id,captured_ms),fill='white')
    detections=[]
    if classification in ('CAT','DOG'):
        x1=.18+(frame_id%10)*.008;box=[x1,.24,x1+.5,.82]
        color=(25,235,90) if classification=='CAT' else (255,70,70)
        draw.rectangle((box[0]*width,box[1]*height,box[2]*width,box[3]*height),outline=color,width=3)
        draw.text((box[0]*width,box[1]*height-18),classification+' 90%',fill=color)
        detections=[{'species':classification,'bbox':box}]
    roi=[.1,.2,.85,.95] if roi_enabled else None
    if roi:draw.rectangle((roi[0]*width,roi[1]*height,roi[2]*width,roi[3]*height),outline=(255,220,0),width=2)
    draw.text((8,height-24),'ROI_ENABLED' if roi_enabled else 'FULL_FRAME - NO TRAY CLAIM',fill='white')
    output=io.BytesIO();image.save(output,format='JPEG',quality=70)
    meta={'producer_epoch':'SIMULATED_WINDOWS_V1','frame_id':frame_id,'metadata_frame_id':frame_id,'overlay_frame_id':frame_id,
          'captured_monotonic_ms':captured_ms,'metadata_monotonic_ms':captured_ms,'width':width,'height':height,
          'source':'SIMULATED','simulated':True,'overlay_applied':True,'classification':classification,
          'confidence':.9 if classification in ('CAT','DOG') else None,'detections':detections,
          'roi_mode':'ROI_ENABLED' if roi_enabled else 'FULL_FRAME','food_roi':roi}
    return output.getvalue(),meta

class SyntheticProducer:
    def __init__(self,hub,fps=6):
        self.hub=hub;self.fps=fps;self.task=None;self.captured=self.encoded=0
    async def run(self):
        while True:
            self.captured+=1 # synthetic capture/AI continue even with no viewers
            if self.hub.demand()>0:
                self.encoded+=1
                species=('CAT','DOG','NONE')[(self.encoded//20)%3]
                data,meta=render_frame(self.encoded,int(self.hub.clock()*1000),species,roi_enabled=self.encoded%40>=20)
                await self.hub.publish(data,meta)
            await asyncio.sleep(1/self.fps)
    async def start(self):self.task=asyncio.create_task(self.run())
    async def stop(self):
        if self.task:
            self.task.cancel()
            try:await self.task
            except asyncio.CancelledError:pass
