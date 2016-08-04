# -*- coding: utf-8 -*-
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.utils import ProceduralCourseTestMixin
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
import datetime
from validator import CourseValid
from django.conf import settings

EVMS_URL = "https://evms.openedu.ru"
EVMS_API_KEY =  "bfuiy3748y5hgfurgh3ri28h"

setattr(settings, 'EVMS_URL', EVMS_URL)
setattr(settings, "EVMS_API_KEY", EVMS_API_KEY)

class VideoValTest(ProceduralCourseTestMixin, ModuleStoreTestCase):

    """Unit tests for video validation"""
    def setUp(self):
        super(VideoValTest, self).setUp()
        self.course = CourseFactory()
        self.chap = ItemFactory.create(
            parent_location=self.course.location,
            category='chapter',
            display_name="Week 1",
            modulestore=self.store,
            publish_item=True,
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        course_key = str(self.course.id)
        self.CV = CourseValid(None, course_key)

    def test_no_vid(self):
        """Видео нет в курсе"""
        rep = self.CV.val_video()
        self.assertEqual(rep.warnings, [])

    def test_vid_YT(self):
        """Видео через рабочую ссылку на ютуб"""
        vid = ItemFactory.create(
            parent_location=self.course.location,
            category='video',
            display_name="nice_youtube_video",
            modulestore=self.store,
            publish_item=True,
            youtube_id_1_0="jNQXAC9IVRw",
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        rep = self.CV.val_video()
        self.assertEqual(rep.warnings, [])


    def test_vid_YT_broken(self):
        """Видео с битой ссылкой на ютуб"""
        vid = ItemFactory.create(
            parent_location=self.course.location,
            category='video',
            display_name="broken_youtube_video",
            modulestore=self.store,
            publish_item=True,
            youtube_id_1_0="jNQXAC9IVRw_foobar",
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        rep = self.CV.val_video()
        self.assertEqual(len(rep.warnings), 1)

    def test_vid_edx(self):
        """Видео через рабочий edx_video_id"""
        pass

    def test_vid_edx_broken(self):
        """Видео с битым edx_video_id"""
        pass
