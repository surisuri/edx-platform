
import ddt
from datetime import timedelta
from django.utils.timezone import now
import mock


from course_modes.models import CourseMode
from openedx.features.course_duration_limits.access import get_user_course_expiration_date, MIN_DURATION, MAX_DURATION
from student.models import CourseEnrollment
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

@ddt.ddt
class CourseExpirationTestCase(ModuleStoreTestCase):
    def setUp(self):
        super(CourseExpirationTestCase, self).setUp()
        self.course = CourseFactory(
            start=now() - timedelta(weeks=10),
        )
        self.user = UserFactory()
    
    def tearDown(self):
        CourseEnrollment.unenroll(self.user, self.course.id)
        super(CourseExpirationTestCase, self).tearDown()
    
    def test_enrollment_mode(self):
        CourseEnrollment.enroll(self.user, self.course.id, CourseMode.VERIFIED)
        result = get_user_course_expiration_date(self.user, self.course)
        self.assertEqual(result, None)

    def test_instructor_paced(self):
        expected_difference = timedelta(weeks=6)
        self.course.self_paced = False
        self.course.end = self.course.start + expected_difference
        enrollment = CourseEnrollment.enroll(self.user, self.course.id, CourseMode.AUDIT)
        result = get_user_course_expiration_date(self.user, self.course)
        self.assertEqual(result, enrollment.created + expected_difference)
    
    def test_instructor_paced_no_end_date(self):
        self.course.self_paced = False
        enrollment = CourseEnrollment.enroll(self.user, self.course.id, CourseMode.AUDIT)
        result = get_user_course_expiration_date(self.user, self.course)
        self.assertEqual(result, enrollment.created + MIN_DURATION)

    @mock.patch("openedx.features.course_duration_limits.access.get_course_run_details")
    @ddt.data(
        [int(MIN_DURATION.days / 7) - 1, MIN_DURATION],
        [7, timedelta(weeks=7)],
        [int(MAX_DURATION.days / 7) + 1, MAX_DURATION],
        [None, MIN_DURATION],
    )
    @ddt.unpack
    def test_self_paced_with_weeks_to_complete(
        self,
        weeks_to_complete,
        expected_difference, 
        mock_get_course_run_details,
    ):
        self.course.self_paced = True
        mock_get_course_run_details.return_value = {'weeks_to_complete': weeks_to_complete}
        enrollment = CourseEnrollment.enroll(self.user, self.course.id, CourseMode.AUDIT)
        result = get_user_course_expiration_date(self.user, self.course)
        self.assertEqual(result, enrollment.created + expected_difference)