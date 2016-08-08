# -*- coding: utf-8 -*-
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from datetime import datetime, timedelta
from validator import CourseValid
from django.conf import settings
from models.settings.course_grading import CourseGradingModel

EVMS_URL = "https://evms.openedu.ru"
EVMS_API_KEY =  "bfuiy3748y5hgfurgh3ri28h"

setattr(settings, "EVMS_URL", EVMS_URL)
setattr(settings, "EVMS_API_KEY", EVMS_API_KEY)


class BaseValTest(ModuleStoreTestCase):
    """ Base class for all following tests """

    def setUp(self):
        super(BaseValTest, self).setUp()
        self.course = CourseFactory(start=datetime.now() - timedelta(days=14))
        self.chapter = ItemFactory.create(parent_location= self.course.location,
            category='chapter',
            start=datetime.now() - timedelta(days=10)
        )
        self.sequential = ItemFactory.create(category='sequential',
            parent_location=self.chapter.location,
            start=datetime.now() - timedelta(days=8))
        self.course_key = self.course.id

    def set_task(self, n_task, type_task, category_task='vertical'):
        for i in range(n_task):
            ItemFactory.create(
                parent_location=self.sequential.location,
                category=category_task,
                format=type_task,
                modulestore=self.store,
            )


class VideoValTest(BaseValTest):
    """Unit tests for CourseValid.val_video"""

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
            start=datetime.now() - timedelta(days=10)
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
            start=datetime.now() - timedelta(days=10)
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()

        self.assertEqual(len(rep.warnings), 1, msg="must be one warning")
        self.assertEqual(len(rep.body), 1, msg="must be one string with warning")

    def test_vid_edx(self):
        """Видео через рабочий edx_video_id"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="nice_edx_id_video",
            modulestore=self.store,
            edx_video_id="WebDevelopment-001-vc16i9zjkv",
        )
        CV = CourseValid(None, str(self.course.id))
        rep = CV.val_video()
        self.assertEqual(len(rep.warnings), 0, msg="must be no warnings, but:{}".format(
            rep.warnings)
        )
        self.assertEqual(len(rep.body), 1, msg="must be one string with video length")

    def test_vid_edx_broken(self):
        """Видео с битым edx_video_id"""
        self.vid = ItemFactory.create(
            parent_location=self.sequential.location,
            category='video',
            display_name="broken_edx_id_video",
            modulestore=self.store,
            edx_video_id="WebDevelopment-001-vc16i9zjkv_foobar",
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

    def test_long_youtube_video(self):
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


class GradingValTest(BaseValTest):
    """UT for CourseValid.val_grading()"""

    def setUp(self):
        """Устанавливает грейдеры на 3 типа заданий и задает им веса"""
        super(GradingValTest, self).setUp()

        self.graders = CourseGradingModel.fetch(self.course.id).graders
        self.graders[0]['min_count'] = 5
        self.graders[1]['min_count'] = 3
        self.graders[0]['weight'] = 33.
        self.graders[1]['weight'] = 27.
        for g in self.graders:
            CourseGradingModel.update_grader_from_json(self.course.id, g, self.user)
        CourseGradingModel.delete_grader(self.course_key, 2, self.user)

    def test_correct_grad(self):
        """Проверка отсутствия ошибок на правильном курсе"""
        self.set_task(n_task=5, type_task="Homework")
        self.set_task(n_task=3, type_task="Lab")
        self.set_task(n_task=1, type_task="Final Exam")
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_grade()
        self.assertEqual(rep.warnings, [])

    def test_need_more_hw(self):
        """
        В курсе меньше заданий чем указано в настройках.
        Предполагается, что заданий в курсе должно быть ровно
        столько, сколько указано в настройках.
        """
        self.set_task(n_task=4, type_task="Homework")
        self.set_task(n_task=3, type_task="Lab")
        self.set_task(n_task=1, type_task="Final Exam")
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_grade()
        self.assertEqual(len(rep.warnings), 1)

    def test_wrong_task_type(self):
        """
        В курсе есть блок с типом задания, которого нет в настройках.
        Теоретически такого не может быть никогда
        """
        self.set_task(n_task=5, type_task="Homework")
        self.set_task(n_task=3, type_task="Lab")
        self.set_task(n_task=1, type_task="Final Exam")
        self.set_task(n_task=1, type_task="Unexpected task type")
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_grade()
        self.assertEqual(len(rep.warnings), 1)

    def test_wrong_weight_sums(self):
        """Сумма весов в настройках не равна 100"""
        self.graders = CourseGradingModel.fetch(self.course.id).graders
        self.graders[0]['weight'] = 103.
        CourseGradingModel.update_grader_from_json(self.course.id, self.graders[0], self.user)

        self.set_task(n_task=5, type_task="Homework")
        self.set_task(n_task=3, type_task="Lab")
        self.set_task(n_task=1, type_task="Final Exam")
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_grade()
        self.assertEqual(len(rep.warnings), 1)


class XmoduleValTest(BaseValTest):
    """UT for CourseValid.val_xmodule()"""

    def test_correct_xmodule(self):
        """Проверка что хороший курс без пустых разделов не вызывает ошибок."""
        v = ItemFactory.create(category="vertical", parent_location=self.sequential.location)
        ItemFactory.create(category="problem", parent_location=v.location)
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_xmodule()
        print(rep)
        self.assertEqual(rep.warnings, [])

    def test_empty_seq(self):
        """Проверяется наличие 2 предупреждений при 2 пустых курсах"""
        ItemFactory.create(category="sequential", parent_location=self.chapter.location)
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_xmodule()
        print(rep)
        self.assertEqual(len(rep.warnings), 2)

    def test_counts(self):
        """Проверяется правильность подсчета в курсе с video и problem"""
        counts = {
            "problem":2,
            "video":3,
        }

        for key in counts:
            for num in range(counts[key]):
                ItemFactory.create(category=key, parent_location=self.sequential.location)

        ItemFactory.create(category="vertical", parent_location=self.sequential.location)
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_xmodule()
        print(rep)
        for b in rep.body:
            type_, count_in_course = b.split(' - ')
            if type_ in counts:
                self.assertEqual(count_in_course, str(counts[type_]))
            elif type_ == "others":
                self.assertEqual(count_in_course, '1')


class DateValTest(BaseValTest):
    """UT for CourseValid.val_dates"""
    def test_correct(self):
        """ Проверка отсутствия ошибок на корректном курсе"""
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(rep.warnings, [])

    def test_vertical_problem_invert_dates(self):
        """
        Проверка ошибки в случае problem с датой старта
        раньшей, чем у ее родителе vertical
        """
        v = ItemFactory.create(category="vertical",
            parent_location=self.sequential.location,
            start = datetime.now() - timedelta(days=4)
        )
        ItemFactory.create(category="problem",
            display_name="wrong_date_problem",
            parent_location=v.location,
            start=datetime.now() - timedelta(days=6)
        )
        ItemFactory.create(category="problem",
            display_name="nice_date_problem",
            parent_location=v.location,
            start=datetime.now() - timedelta(days=3)
        )
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(len(rep.warnings), 1)
        wrong_date_caught = "wrong_date_problem" in rep.warnings[0]
        self.assertTrue(wrong_date_caught)
        nice_date_passed = "nice_date_problem" in rep.warnings[0]
        self.assertFalse(nice_date_passed)

    def test_future_course(self):
        """Проверка ошибки в случае даты старта всех блоков более завтра"""
        t = timedelta(weeks=100)
        course = CourseFactory(start=datetime.now() - timedelta(days=14)+t)
        chapter = ItemFactory.create(parent_location=course.location,
            category='chapter',
            start=datetime.now() - timedelta(days=10)+t
        )
        sequential = ItemFactory.create(category='sequential',
            parent_location=chapter.location,
            start=datetime.now() - timedelta(days=8)+t
        )
        course_key = course.id
        CV = CourseValid(None, str(course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(len(rep.warnings), 1)

   