# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from django.conf import settings
from models.settings.course_grading import CourseGradingModel
from cms.djangoapps.contentstore.views.tests.test_item import ItemTest
from cms.djangoapps.contentstore.utils import reverse_usage_url

from validator import CourseValid

EVMS_URL = "https://evms.openedu.ru"
EVMS_API_KEY =  "bfuiy3748y5hgfurgh3ri28h"

setattr(settings, "EVMS_URL", EVMS_URL)
setattr(settings, "EVMS_API_KEY", EVMS_API_KEY)


class BaseValTest(ModuleStoreTestCase):
    """ Base class for all following tests """

    def setUp(self):
        super(BaseValTest, self).setUp()
        self.course = CourseFactory(start=self.days_ago(14), publish_item=True)

        self.chapter = ItemFactory.create(parent_location= self.course.location,
            category='chapter',
            start=self.days_ago(10),
            publish_item=True,
        )

        self.sequential = ItemFactory.create(parent_location=self.chapter.location,
            category='sequential',
            start=self.days_ago(8),
            publish_item=True,
        )

        self.course_key = self.course.id

    def set_task(self, n_task, type_task, category_task='vertical'):
        for i in range(n_task):
            ItemFactory.create(
                parent_location=self.sequential.location,
                category=category_task,
                format=type_task,
                modulestore=self.store,
            )

    def days_ago(self, days=10):
        return datetime.now() - timedelta(days=days)


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
            start=self.days_ago(days=10)
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
            start=self.days_ago(days=10)
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
        rep = CV.val_module()
        print(rep)
        self.assertEqual(rep.warnings, [])

    def test_empty_seq(self):
        """Проверяется наличие 2 предупреждений при 2 пустых курсах"""
        ItemFactory.create(category="sequential", parent_location=self.chapter.location)
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_module()
        print(rep)
        self.assertEqual(len(rep.warnings), 2)

    def test_counts(self):
        """Проверяется правильность подсчета в курсе с video и problem"""
        target_counts = {
            "problem":2,
            "video":3,
        }

        for key in target_counts:
            for num in range(target_counts[key]):
                ItemFactory.create(category=key, parent_location=self.sequential.location)

        ItemFactory.create(category="vertical", parent_location=self.sequential.location)
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_module()
        print(rep)
        for b in rep.body:
            type_, count_in_course = b.split(' - ')
            if type_ in target_counts:
                self.assertEqual(count_in_course, str(target_counts[type_]))
            elif type_ == "others":
                self.assertEqual(count_in_course, '1')


class DateBaseValTest(BaseValTest, ItemTest):
        #print('after', self.chapter.published_by, self.chapter.published_on,
              #self.sequential.published_by, self.sequential.published_on)
    def setUp(self):
        super(DateBaseValTest, self).setUp()
        self.make_them_public()



    def make_them_public(self):
        objs = [self.course, self.chapter, self.sequential]
        for x in objs:
            problem_usage_key = x.location #self.response_usage_key(x)
            problem_update_url = reverse_usage_url("xblock_handler", problem_usage_key)
            self.client.ajax_post(
                problem_update_url,
                data={'publish': 'make_public'}
            )
        #resp = self.create_xblock(parent_usage_key=self.seq_usage_key, category='problem', boilerplate=template_id)
        #self.problem_usage_key = self.response_usage_key(resp)
        #self.problem_update_url = reverse_usage_url("xblock_handler", self.problem_usage_key)#
        #self.course_update_url = reverse_usage_url("xblock_handler", self.usage_key)


class DateValTest(BaseValTest):
    """UT for CourseValid.val_dates"""

    def test_correct_dates(self):
        """ Проверка отсутствия ошибок на корректном курсе"""
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(rep.warnings, [])

    def test_child_parent_invert_dates(self):
        """
        Проверка ошибки в случае problem с датой старта
        раньшей, чем у ее родителе vertical
        """
        v = ItemFactory.create(category="vertical",
            parent_location=self.sequential.location,
            start = self.days_ago(days=4)
        )
        ItemFactory.create(category="problem",
            display_name="wrong_date_problem",
            parent_location=v.location,
            start=self.days_ago(days=6)
        )
        ItemFactory.create(category="problem",
            display_name="nice_date_problem",
            parent_location=v.location,
            start=self.days_ago(days=3)
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
        course = CourseFactory(start=self.days_ago(days=14)+t)
        chapter = ItemFactory.create(parent_location=course.location,
            category='chapter',
            start=self.days_ago(days=10)+t
        )
        sequential = ItemFactory.create(category='sequential',
            parent_location=chapter.location,
            start=self.days_ago(days=8)+t
        )
        course_key = course.id
        CV = CourseValid(None, str(course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(len(rep.warnings), 1)

    def test_invisible_course(self):
        items = self.store.get_items(self.course_key)
        for i in items:
            if i.category == "course":
                continue
            i.visible_to_staff_only = True
            self.store.update_item(i, self.user.id)
        ItemFactory.create(parent_location=self.sequential.location,
            category='vertical',
            start=self.days_ago(days=-5)
        )
        ItemFactory.create(parent_location=self.sequential.location,
            category='vertical',
            start=self.days_ago(days=5),
            visible_to_staff_only=True,
        )
        CV = CourseValid(None, str(self.course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(len(rep.warnings), 1)
        visibility_warning = "visib" in rep.warnings[0]
        self.assertTrue(visibility_warning)
    #TODO check if it is possible to create unpublished course. Search DIRECT_ONLY_CATEGORIES
    def test_unpublished_course(self):

        course = CourseFactory(start=self.days_ago(days=14),
                               display_name="unpubl_course",
                               publish_item=False
                               )
        chapter = ItemFactory.create(parent_location=course.location,
                                     category='chapter',
                                     display_name='unp_ch',
                                     start=self.days_ago(days=10),
                                     publish_item=False
                                     )
        sequential = ItemFactory.create(category='sequential',
                                        parent_location=chapter.location,
                                        display_name='unp_seq',
                                        start=self.days_ago(days=8),
                                        publish_item=False
                                        )
        ItemFactory.create(category='sequential',
                           parent_location=chapter.location,
                           display_name='unp_seq2',
                           start=self.days_ago(days=8),
                           publish_item=False
                           )
        ItemFactory.create(category='sequential',
                           parent_location=chapter.location,
                           display_name='unp_seq3',
                           start=self.days_ago(days=8),
                           publish_item=False
                           )
        ItemFactory.create(category='vertical',
                           parent_location=sequential.location,
                           display_name='v1',
                           start=self.days_ago(days=7),
                           publish_item=False
                           )
        ItemFactory.create(category='vertical',
                           parent_location=sequential.location,
                           display_name='v2',
                           start=self.days_ago(days=7),
                           publish_item=False
                           )

        c = lambda x : self.store.has_published_version(x)
        print("!",c(course), c(chapter), c(sequential))
        course_key = course.id
        CV = CourseValid(None, str(course_key))
        rep = CV.val_dates()
        print(rep)
        self.assertEqual(len(rep.warnings), 1)

        self.assertTrue(False)