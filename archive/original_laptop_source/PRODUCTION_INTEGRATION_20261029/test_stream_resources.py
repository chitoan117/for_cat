import asyncio
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
sys.path.insert(0,str(ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028'))
from synthetic_video import render_frame
from app.camera.live_stream import FrameHub,VideoSettings

def test_duplicate_watermark_survives_stale_and_epoch_retirement():
    async def go():
        now=[100.];h=FrameHub(VideoSettings(enabled=True,source='SIMULATED'),lambda:now[0])
        data,meta=render_frame(10,100000);await h.publish(data,meta)
        now[0]=103;assert h.latest() is None
        data,meta=render_frame(10,103000)
        with pytest.raises(ValueError,match='duplicate'):await h.publish(data,meta)
        data,meta=render_frame(1,103000);meta['producer_epoch']='new_epoch';await h.publish(data,meta)
        assert h.status()['producer_epoch']=='new_epoch'
        now[0]=106;data,meta=render_frame(11,106000)
        with pytest.raises(ValueError):await h.publish(data,meta)
        await h.close()
    asyncio.run(go())
def test_multiple_viewers_one_slot_cleanup_and_no_database(tmp_path):
    async def go():
        now=[100.];h=FrameHub(VideoSettings(enabled=True,source='SIMULATED',max_viewers=4),lambda:now[0])
        data,meta=render_frame(1,100000);await h.publish(data,meta)
        viewers=[h.acquire() for _ in range(4)]
        with pytest.raises(Exception) as e:h.acquire()
        assert e.value.status_code==429
        for n in range(2,30):
            data,meta=render_frame(n,100000);await h.publish(data,meta)
        assert h.latest()[1]['frame_id']==29 and h.status()['frame_slots']==1
        assert h.status()['buffered_bytes']<=524288
        for viewer in viewers:h.release(viewer)
        assert h.status()['viewers']==0 and not list(tmp_path.iterdir())
        await h.close()
    asyncio.run(go())
