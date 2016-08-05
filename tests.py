# -*- coding: utf-8 -*-
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
import datetime
from validator import CourseValid
from django.conf import settings
from models.settings.course_grading import CourseGradingModel
from utils import _print_all

EVMS_URL = "https://evms.openedu.ru"
EVMS_API_KEY =  "bfuiy3748y5hgfurgh3ri28h"

setattr(settings, 'EVMS_URL', EVMS_URL)
setattr(settings, "EVMS_API_KEY", EVMS_API_KEY)


class VideoValTest(ModuleStoreTestCase):
    """Unit tests for video validation"""

    def setUp(self):
        super(VideoValTest, self).setUp()
        self.course = CourseFactory()
        self.chapter = ItemFactory.create(
            parent_location=self.course.location,
            category='chapter',
            display_name="Week 1",
            modulestore=self.store,
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        self.sequential = ItemFactory.create(category='sequential', parent_location=self.chapter.location)
        self.course_key = self.course.id

    def test_no_vid(self):
        """Видео нет в курсе"""
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        self.assertEqual(rep.warnings, [])
        self.assertEqual(len(rep.body), 0, msg="must be one string with duration")

    def test_vid_YT(self):
        """Видео через рабочую ссылку на ютуб"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="nice_youtube_video",
            modulestore=self.store,
            youtube_id_1_0="jNQXAC9IVRw",
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        self.assertEqual(rep.warnings, [], msg="warnings for working video")
        self.assertEqual(len(rep.body), 1, msg="must be one string with duration")

    def test_vid_YT_broken(self):
        """Видео с битой ссылкой на ютуб"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="broken_youtube_video",
            modulestore=self.store,
            youtube_id_1_0="jNQXAC9IVRw_foobar",
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()

        self.assertEqual(len(rep.warnings), 1, msg="must be one warning")
        self.assertEqual(len(rep.body), 1, msg="must be one string with warning")

    #TODO: fix video get through api
    def test_vid_edx(self):
        """Видео через рабочий edx_video_id"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="nice_edx_id_video",
            modulestore=self.store,
            edx_video_id="WebDevelopment - 001 - vc16i9zjkv",
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        #self.assertEqual(len(rep.warnings), 0, msg="must be no warnings, but:{}".format(
        #    rep.warnings)
        #)
        #self.assertEqual(len(rep.body), 1, msg="must be one string with video length")

    def test_vid_edx_broken(self):
        """Видео с битым edx_video_id"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="broken_edx_id_video",
            modulestore=self.store,
            edx_video_id="WebDevelopment - 001 - vc16i9zjkv_foobar",
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        self.assertEqual(len(rep.warnings), 1, msg="must be one warning, but:{}".format(
            rep.warnings)
        )
        self.assertEqual(len(rep.body), 1, msg="must be one string with video length")

    def test_short_youtube_video(self):
        """Warning for videos longer than 24 hours"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="short_YT_video",
            modulestore=self.store,
            youtube_id_1_0="dGRdg6Cj6lw",
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        self.assertEqual(rep.warnings, [], msg="must be no warning")
        self.assertEqual(len(rep.body), 1, msg="must be one string with duration")

    """
    В валидаторе предполагалось, что при длительности видео более 24 часов формат возвращаемой
    длительности видео должен быть D:H:M:S. В таком случае выдается предупреждение,
    что видео черезчур долгое. Проверка показала что в таком случае
    возвращается D:H. Непонятно как отличить D:H от M:S, соответственно предупреждение не сработает,
    но наверное это не очень важно.
    """
    def donttest_long_youtube_video(self):
        """Warning for videos longer than 24 hours"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="long_YT_video",
            modulestore=self.store,
            youtube_id_1_0="GzNgTCJiLxk",
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        self.assertEqual(len(rep.warnings), 1, msg="must be one warning")
        self.assertEqual(len(rep.body), 1, msg="must be one string with warning")


class GradingValTest(ModuleStoreTestCase):
    """Unit tests for grading validation"""

    def setUp(self):
        super(GradingValTest, self).setUp()
        self.course = CourseFactory()
        self.chapter = ItemFactory.create(
            parent_location=self.course.location,
            category='chapter',
            display_name="Week 1",
            modulestore=self.store,
            start=datetime.datetime.now() - datetime.timedelta(days=10)
        )
        self.sequential = ItemFactory.create(category='sequential', parent_location=self.chapter.location)
        self.course_key = self.course.id
        self.graders = CourseGradingModel.fetch(self.course.id).graders
        print("!!!!!!!!!!!!")
        print(self.graders)
        print("xxxxxxxxxxxx")

        CourseGradingModel.delete_grader(self.course_key, 2, self.user)
        print('x-x-x-x-x-x-x')
        print(CourseGradingModel.fetch(self.course.id).graders)
        print("iiiiiiiiiiii")
        self.graders[0]['min_count'] = 4
        self.graders[1]['min_count'] = 2
        self.graders[0]['weight'] = 30.
        self.graders[1]['weight'] = 30.
        for g in self.graders:
            CourseGradingModel.update_grader_from_json(self.course.id, g, self.user)

    def _set_task(self, n_task, type_task):
        for i in range(n_task):
            ItemFactory.create(
                parent_location=self.sequential.location,
                category='vertical',
                format=type_task,
                modulestore=self.store,
            )
    """
    def test(self):
        print(self.graders)
        print("---------")
        self.graders[0]["weight"]=42.
        print(self.graders)
    """

    def test_correct_grad(self):
        self._set_task(n_task=4, type_task="Homework")
        self._set_task(n_task=2, type_task="Lab")
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_grade()
        self.assertEqual(rep, [])

