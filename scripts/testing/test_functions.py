"""Function tests for the Record Keeper document archiving system.

One class per module, one test per function. Run with run_tests.bat; it uses
test_settings.py, so nothing here touches the real database, Cloudinary or email.
"""
import io
import zipfile
from datetime import date, timedelta
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Office, User
from documents.models import AccessLog, Attachment, Document, DocumentType, Notification

PW = "Archive-Pass-2026!"


def pdf_bytes(text="Test page"):
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(80, 700, text)
    pdf.save()
    return buffer.getvalue()


def png_bytes():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buffer, "PNG")
    return buffer.getvalue()


def docx_bytes(text):
    """The smallest Word file that Word (and mammoth) will open."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
                   'officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                   'relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                   f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')
    return buffer.getvalue()


class Base(TestCase):
    def setUp(self):
        cache.clear()  # sign-in failure counts must not leak between tests
        self.office = Office.objects.create(name="Office of the Mayor")
        self.superadmin = User.objects.create_user(
            "super1", email="super1@example.com", password=PW, role=User.Role.SUPERADMIN,
            first_name="Sofia", last_name="Reyes",
        )
        self.admin = User.objects.create_user(
            "admin1", email="admin1@example.com", password=PW, role=User.Role.ADMIN, office=self.office,
        )
        self.staff = User.objects.create_user(
            "staff1", email="staff1@example.com", password=PW, role=User.Role.USER, office=self.office,
        )

    def doc(self, **kwargs):
        values = dict(
            doc_type=DocumentType.MEMORANDUM, series_year=2026, subject="Budget hearing schedule",
            date_issued=date(2026, 3, 2), created_by=self.admin,
            classification=Document.Classification.PUBLIC,
        )
        values.update(kwargs)
        return Document.objects.create(**values)

    def doc_with_file(self, name, data, **kwargs):
        document = self.doc(**kwargs)
        document.file.save(name, SimpleUploadedFile(name, data), save=True)
        return document

    def form_data(self, **kwargs):
        data = dict(
            doc_type="MEMO", series_year=2026, number="", subject="Clean-up drive", description="",
            date_issued="2026-04-01", effectivity_date="", originating_office="Office of the Mayor",
            signatory="Municipal Mayor", addressee="All department heads", keywords="clean-up",
            status="ACTIVE", classification="PUBLIC", physical_location="Cabinet 1",
            related_to="", indorsement_level="",
        )
        data.update(kwargs)
        return data

    def signed_in(self, session):
        return session.get("_auth_user_id")


# ---------------------------------------------------------------- M01
class M01_SignInAndSignOut(Base):
    def test_A01_sign_in_page_opens(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome Back")

    def test_A02_correct_password_signs_in_and_is_logged(self):
        response = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": PW})
        self.assertRedirects(response, reverse("documents:dashboard"), fetch_redirect_response=False)
        self.assertEqual(int(self.signed_in(self.client.session)), self.staff.pk)
        self.assertTrue(AccessLog.objects.filter(user=self.staff, action=AccessLog.Action.LOGIN).exists())

    def test_A03_wrong_password_is_refused(self):
        response = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": "not-it"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.signed_in(self.client.session))

    def test_A04_disabled_account_is_told_it_is_disabled(self):
        self.staff.is_active = False
        self.staff.save()
        response = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": PW})
        self.assertContains(response, "has been disabled")

    def test_A05_pending_account_is_told_to_wait(self):
        self.staff.is_active = False
        self.staff.approval_status = User.Approval.PENDING
        self.staff.save()
        response = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": PW})
        self.assertContains(response, "waiting for approval")

    def test_A06_sign_out_ends_the_session_and_is_logged(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.signed_in(self.client.session))
        self.assertTrue(AccessLog.objects.filter(user=self.staff, action=AccessLog.Action.LOGOUT).exists())

    def wrong(self, username, times):
        for _ in range(times):
            self.client.post(reverse("accounts:login"), {"username": username, "password": "not-it"})

    def test_A08_five_wrong_passwords_pause_the_account(self):
        self.wrong("staff1", 5)
        response = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": PW})
        self.assertContains(response, "Too many wrong passwords")
        self.assertIsNone(self.signed_in(self.client.session))
        self.assertTrue(AccessLog.objects.filter(action=AccessLog.Action.DENIED,
                                                 note__icontains="too many wrong passwords").exists())

    def test_A09_correct_password_before_the_limit_resets_the_count(self):
        self.wrong("staff1", 4)
        self.client.post(reverse("accounts:login"), {"username": "staff1", "password": PW})
        self.client.logout()
        self.wrong("staff1", 4)
        response = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": PW})
        self.assertRedirects(response, reverse("documents:dashboard"), fetch_redirect_response=False)

    def test_A10_lockout_also_applies_to_names_that_do_not_exist(self):
        self.wrong("ghost-user", 5)
        response = self.client.post(reverse("accounts:login"), {"username": "ghost-user", "password": "x"})
        self.assertContains(response, "Too many wrong passwords")

    def test_A11_one_paused_account_does_not_affect_another(self):
        self.wrong("staff1", 5)
        response = self.client.post(reverse("accounts:login"), {"username": "admin1", "password": PW})
        self.assertRedirects(response, reverse("documents:dashboard"), fetch_redirect_response=False)

    def test_A07_pages_need_a_signed_in_user(self):
        for name in ("documents:dashboard", "documents:document_list", "accounts:profile"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), response["Location"], name)


# ---------------------------------------------------------------- M02
class M02_TwoStepSignIn(Base):
    def setUp(self):
        super().setUp()
        sender = patch("accounts.brevo.send_email", return_value=(True, ""))
        self.send = sender.start()
        self.addCleanup(sender.stop)
        code = patch("accounts.twofactor.new_code", return_value="246810")
        code.start()
        self.addCleanup(code.stop)

    def password_step(self):
        return self.client.post(reverse("accounts:login"), {"username": "super1", "password": PW})

    def test_B01_password_alone_does_not_sign_a_super_admin_in(self):
        response = self.password_step()
        self.assertRedirects(response, reverse("accounts:verify"), fetch_redirect_response=False)
        self.assertIsNone(self.signed_in(self.client.session))

    def test_B02_emailed_code_completes_the_sign_in(self):
        self.password_step()
        self.assertEqual(self.client.get(reverse("accounts:verify")).status_code, 200)
        self.assertEqual(self.send.call_args[0][0], "super1@example.com")
        response = self.client.post(reverse("accounts:verify"), {"code": "246810"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.signed_in(self.client.session)), self.superadmin.pk)

    def test_B03_wrong_code_is_refused(self):
        self.password_step()
        self.client.get(reverse("accounts:verify"))
        response = self.client.post(reverse("accounts:verify"), {"code": "000000"})
        self.assertContains(response, "not right")
        self.assertIsNone(self.signed_in(self.client.session))

    def test_B04_five_wrong_codes_end_the_attempt(self):
        self.password_step()
        self.client.get(reverse("accounts:verify"))
        for _ in range(4):
            self.client.post(reverse("accounts:verify"), {"code": "000000"})
        response = self.client.post(reverse("accounts:verify"), {"code": "000000"})
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)

    def test_B05_code_page_without_the_password_step_goes_back(self):
        response = self.client.get(reverse("accounts:verify"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)

    def test_B06_new_code_is_held_back_for_a_minute(self):
        self.password_step()
        self.client.get(reverse("accounts:verify"))
        response = self.client.post(reverse("accounts:verify"), {"resend": "1"}, follow=True)
        self.assertContains(response, "wait a moment")


# ---------------------------------------------------------------- M03
class M03_SignUpAndApproval(Base):
    def signup(self, **kwargs):
        data = dict(
            username="jdelacruz", first_name="Juan", last_name="Dela Cruz", email="juan@example.com",
            office_name="office of the mayor", position="Clerk", contact_number="",
            requested_role="USER", password1=PW, password2=PW,
        )
        data.update(kwargs)
        return self.client.post(reverse("accounts:signup"), data)

    def test_C01_sign_up_page_opens_with_office_as_a_text_box(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="text" name="office_name"')
        self.assertNotContains(response, "<select name=\"office")

    def test_C02_request_creates_a_locked_pending_account(self):
        response = self.signup()
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        user = User.objects.get(username="jdelacruz")
        self.assertFalse(user.is_active)
        self.assertEqual(user.approval_status, User.Approval.PENDING)
        self.assertEqual(user.role, User.Role.USER)

    def test_C03_typed_office_matches_an_existing_one_ignoring_capitals(self):
        self.signup()
        self.assertEqual(User.objects.get(username="jdelacruz").office, self.office)
        self.assertEqual(Office.objects.count(), 1)

    def test_C04_new_office_name_opens_a_new_office(self):
        self.signup(office_name="  Treasurer's   Office ")
        self.assertEqual(User.objects.get(username="jdelacruz").office.name, "Treasurer's Office")

    def test_C05_email_already_in_use_is_refused(self):
        response = self.signup(email="admin1@example.com")
        self.assertContains(response, "already uses this email")
        self.assertFalse(User.objects.filter(username="jdelacruz").exists())

    def test_C06_super_admins_are_notified_of_the_request(self):
        self.signup()
        self.assertTrue(Notification.objects.filter(
            recipient=self.superadmin, verb__icontains="requested an account").exists())

    def test_C07_super_admin_approves_with_a_role(self):
        self.signup()
        applicant = User.objects.get(username="jdelacruz")
        self.client.force_login(self.superadmin)
        self.client.post(reverse("accounts:account_request_decision", args=[applicant.pk, "approve"]),
                         {"role": "ADMIN"})
        applicant.refresh_from_db()
        self.assertTrue(applicant.is_active)
        self.assertEqual(applicant.role, User.Role.ADMIN)
        self.assertEqual(applicant.approval_status, User.Approval.APPROVED)
        self.assertTrue(Notification.objects.filter(recipient=applicant).exists())

    def test_C08_super_admin_rejects_a_request(self):
        self.signup()
        applicant = User.objects.get(username="jdelacruz")
        self.client.force_login(self.superadmin)
        self.client.post(reverse("accounts:account_request_decision", args=[applicant.pk, "reject"]))
        applicant.refresh_from_db()
        self.assertFalse(applicant.is_active)
        self.assertEqual(applicant.approval_status, User.Approval.REJECTED)

    def test_C09_only_the_super_admin_sees_account_requests(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:account_requests")).status_code, 403)
        self.client.force_login(self.superadmin)
        self.assertEqual(self.client.get(reverse("accounts:account_requests")).status_code, 200)

    def test_C10_approved_applicant_can_sign_in(self):
        self.signup()
        applicant = User.objects.get(username="jdelacruz")
        self.client.force_login(self.superadmin)
        self.client.post(reverse("accounts:account_request_decision", args=[applicant.pk, "approve"]),
                         {"role": "USER"})
        self.client.logout()
        response = self.client.post(reverse("accounts:login"), {"username": "jdelacruz", "password": PW})
        self.assertRedirects(response, reverse("documents:dashboard"), fetch_redirect_response=False)


# ---------------------------------------------------------------- M04
class M04_PasswordRecovery(Base):
    def setUp(self):
        super().setUp()
        sender = patch("accounts.brevo.send_email", return_value=(True, ""))
        self.send = sender.start()
        self.addCleanup(sender.stop)
        code = patch("accounts.twofactor.new_code", return_value="135790")
        code.start()
        self.addCleanup(code.stop)

    def ask(self, identifier):
        return self.client.post(reverse("accounts:password_reset"), {"identifier": identifier})

    def test_D01_forgot_password_page_opens(self):
        self.assertEqual(self.client.get(reverse("accounts:password_reset")).status_code, 200)

    def test_D02_emailed_code_sets_a_new_password(self):
        response = self.ask("staff1")
        self.assertRedirects(response, reverse("accounts:password_reset_confirm"), fetch_redirect_response=False)
        self.assertEqual(self.send.call_args[0][0], "staff1@example.com")
        response = self.client.post(reverse("accounts:password_reset_confirm"), {
            "code": "135790", "new_password1": "Fresh-Pass-2027!", "new_password2": "Fresh-Pass-2027!"})
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("Fresh-Pass-2027!"))

    def test_D03_wrong_code_leaves_the_password_alone(self):
        self.ask("staff1")
        response = self.client.post(reverse("accounts:password_reset_confirm"), {
            "code": "000000", "new_password1": "Fresh-Pass-2027!", "new_password2": "Fresh-Pass-2027!"})
        self.assertContains(response, "not right")
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password(PW))

    def test_D04_unknown_account_gets_the_same_answer(self):
        response = self.ask("nobody-here")
        self.assertRedirects(response, reverse("accounts:password_reset_confirm"), fetch_redirect_response=False)
        self.send.assert_not_called()

    def test_D05_account_without_email_gets_the_same_answer(self):
        self.staff.email = ""
        self.staff.save()
        response = self.ask("staff1")
        self.assertRedirects(response, reverse("accounts:password_reset_confirm"), fetch_redirect_response=False)
        self.send.assert_not_called()

    def test_D06_email_address_works_as_well_as_username(self):
        self.ask("STAFF1@example.com")
        self.assertEqual(self.send.call_args[0][0], "staff1@example.com")

    def test_D07_signed_in_user_changes_own_password(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("accounts:password_change"), {
            "old_password": PW, "new_password1": "Fresh-Pass-2027!", "new_password2": "Fresh-Pass-2027!"})
        self.assertEqual(response.status_code, 302)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("Fresh-Pass-2027!"))


# ---------------------------------------------------------------- M05
class M05_Profile(Base):
    def test_E01_profile_page_opens(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_E02_user_updates_own_details(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Ana", "last_name": "Santos", "email": "ana@example.com", "contact_number": ""})
        self.assertRedirects(response, reverse("accounts:profile"), fetch_redirect_response=False)
        self.staff.refresh_from_db()
        self.assertEqual((self.staff.first_name, self.staff.email), ("Ana", "ana@example.com"))

    def test_E03_email_of_another_account_is_refused(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Ana", "last_name": "Santos", "email": "admin1@example.com", "contact_number": ""})
        self.assertContains(response, "already uses this email")


# ---------------------------------------------------------------- M06
class M06_AccountManagement(Base):
    def update_data(self, user, **kwargs):
        data = dict(first_name=user.first_name, last_name=user.last_name, email=user.email,
                    role=user.role, office=user.office_id or "", position="", contact_number="",
                    is_active="on")
        data.update(kwargs)
        return data

    def test_F01_account_list_opens_for_admins_not_staff(self):
        for user, expected in ((self.admin, 200), (self.superadmin, 200), (self.staff, 403)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, expected, user)

    def test_F02_account_search_finds_people_by_office(self):
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse("accounts:user_list"), {"q": "Mayor"})
        self.assertContains(response, "staff1")
        self.assertContains(response, "admin1")

    def test_F03_super_admin_creates_an_account(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse("accounts:user_create"), {
            "username": "new1", "first_name": "New", "last_name": "Clerk", "email": "new1@example.com",
            "role": "USER", "office": self.office.pk, "position": "Clerk", "contact_number": "",
            "password1": PW, "password2": PW})
        self.assertRedirects(response, reverse("accounts:user_list"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="new1", is_active=True).exists())
        self.assertTrue(AccessLog.objects.filter(action=AccessLog.Action.USER_MANAGE,
                                                 note__icontains="new1").exists())

    def test_F04_administrator_cannot_create_accounts(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:user_create")).status_code, 403)

    def test_F05_super_admin_changes_another_persons_role(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse("accounts:user_update", args=[self.staff.pk]),
                                    self.update_data(self.staff, role="ADMIN"))
        self.assertEqual(response.status_code, 302)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.role, User.Role.ADMIN)

    def test_F06_super_admin_disables_an_account(self):
        self.client.force_login(self.superadmin)
        data = self.update_data(self.staff)
        data.pop("is_active")
        self.client.post(reverse("accounts:user_update", args=[self.staff.pk]), data)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_F07_super_admin_edits_own_account(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse("accounts:user_update", args=[self.superadmin.pk]),
                                    self.update_data(self.superadmin, position="Records Head"))
        self.assertEqual(response.status_code, 302)
        self.superadmin.refresh_from_db()
        self.assertEqual(self.superadmin.position, "Records Head")
        self.assertEqual(self.superadmin.role, User.Role.SUPERADMIN)

    def test_F08_super_admin_sets_a_new_password_for_someone(self):
        self.client.force_login(self.superadmin)
        response = self.client.post(reverse("accounts:user_password", args=[self.staff.pk]), {
            "password1": "Temp-Pass-2026!", "password2": "Temp-Pass-2026!"})
        self.assertEqual(response.status_code, 302)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("Temp-Pass-2026!"))


# ---------------------------------------------------------------- M07
class M07_Offices(Base):
    def test_G01_office_list_opens_for_every_role(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("accounts:office_list"))
        self.assertContains(response, "Office of the Mayor")

    def test_G02_administrator_adds_an_office(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("accounts:office_create"),
                                    {"name": "Budget Office", "description": "", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Office.objects.filter(name="Budget Office").exists())

    def test_G03_staff_cannot_add_an_office(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("accounts:office_create")).status_code, 403)

    def test_G04_administrator_renames_an_office(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:office_update", args=[self.office.pk]),
                         {"name": "Office of the Municipal Mayor", "description": "", "is_active": "on"})
        self.office.refresh_from_db()
        self.assertEqual(self.office.name, "Office of the Municipal Mayor")

    def test_G05_office_notice_reaches_members_but_not_the_sender(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("accounts:office_notify", args=[self.office.pk]),
                                    {"message": "Please bring your IDs on Monday."})
        self.assertRedirects(response, reverse("accounts:office_list"), fetch_redirect_response=False)
        self.assertTrue(Notification.objects.filter(recipient=self.staff, verb__icontains="IDs").exists())
        self.assertFalse(Notification.objects.filter(recipient=self.admin).exists())

    def test_G06_notice_to_an_office_with_nobody_else_is_refused(self):
        empty = Office.objects.create(name="Empty Office")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("accounts:office_notify", args=[empty.pk]),
                                    {"message": "Hello"}, follow=True)
        self.assertContains(response, "no active members")
        self.assertEqual(Notification.objects.count(), 0)

    def test_G07_staff_cannot_send_office_notices(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("accounts:office_notify", args=[self.office.pk])).status_code, 403)


# ---------------------------------------------------------------- M08
class M08_Notifications(Base):
    def test_H01_notification_list_shows_and_marks_read(self):
        note = Notification.objects.create(recipient=self.staff, verb="Test notice")
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("accounts:notification_list")), "Test notice")
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_H02_bell_reports_the_unread_count(self):
        Notification.objects.create(recipient=self.staff, verb="One")
        self.assertEqual(self.client.get(reverse("accounts:notifications_poll")).status_code, 401)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("accounts:notifications_poll"))
        self.assertEqual(response["X-Unread-Count"], "1")

    def test_H03_opening_a_notification_marks_it_read(self):
        document = self.doc()
        note = Notification.objects.create(recipient=self.staff, verb="Filed", document=document)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("accounts:notification_open", args=[note.pk]))
        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_H04_mark_all_as_read(self):
        Notification.objects.create(recipient=self.staff, verb="One")
        Notification.objects.create(recipient=self.staff, verb="Two")
        self.client.force_login(self.staff)
        self.client.get(reverse("accounts:notifications_mark_all_read"))
        self.assertFalse(Notification.objects.filter(recipient=self.staff, is_read=False).exists())


# ---------------------------------------------------------------- M09
class M09_OverviewAndSearch(Base):
    def setUp(self):
        super().setUp()
        self.alpha = self.doc(subject="Alpha budget hearing", date_issued=date(2026, 2, 1))
        self.bravo = self.doc(subject="Bravo fiesta preparations", date_issued=date(2026, 6, 15),
                              keywords="fiesta")

    def test_I01_overview_opens_for_every_role(self):
        for user in (self.staff, self.admin, self.superadmin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("documents:dashboard")).status_code, 200, user)

    def test_I02_keyword_search(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_list"), {"q": "fiesta"})
        self.assertContains(response, "Bravo fiesta")
        self.assertNotContains(response, "Alpha budget")

    def test_I03_search_by_number_and_series_year(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_list"),
                                   {"number": self.bravo.number, "series_year": 2026})
        self.assertContains(response, "Bravo fiesta")
        self.assertNotContains(response, "Alpha budget")

    def test_I04_search_by_date_range(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_list"),
                                   {"date_from": "2026-01-01", "date_to": "2026-03-31"})
        self.assertContains(response, "Alpha budget")
        self.assertNotContains(response, "Bravo fiesta")

    def test_I05_reversed_date_range_is_flagged(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_list"),
                                   {"date_from": "2026-12-31", "date_to": "2026-01-01"})
        self.assertContains(response, "end date falls before")

    def test_I06_searches_are_logged(self):
        self.client.force_login(self.staff)
        self.client.get(reverse("documents:document_list"), {"q": "fiesta"})
        self.assertTrue(AccessLog.objects.filter(user=self.staff, action=AccessLog.Action.SEARCH).exists())

    def test_I07_live_search_suggestions(self):
        self.assertEqual(self.client.get(reverse("documents:document_suggest"), {"q": "fiesta"}).status_code, 401)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("documents:document_suggest"), {"q": "fiesta"}), "fiesta")

    def test_I08_folder_opens_with_year_sub_folders(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("documents:document_folder", args=["MEMO"]))
        self.assertContains(response, "2026")

    def test_I09_staff_do_not_find_internal_records(self):
        self.doc(subject="Charlie internal memo", classification=Document.Classification.INTERNAL)
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(reverse("documents:document_list"), {"q": "Charlie"}),
                               "Charlie internal")


# ---------------------------------------------------------------- M10
class M10_FilingAndEditing(Base):
    def file_it(self, user=None, **kwargs):
        self.client.force_login(user or self.admin)
        return self.client.post(reverse("documents:document_create"), self.form_data(**kwargs))

    def test_J01_admin_files_a_document_and_gets_the_next_number(self):
        self.doc()
        response = self.file_it(file=SimpleUploadedFile("memo.pdf", pdf_bytes(), "application/pdf"))
        self.assertEqual(response.status_code, 302)
        filed = Document.objects.get(subject="Clean-up drive")
        self.assertEqual(filed.number, 2)
        self.assertTrue(filed.file.name.endswith(".pdf"))
        self.assertTrue(AccessLog.objects.filter(action=AccessLog.Action.CREATE, document=filed).exists())

    def test_J02_public_filing_notifies_other_users(self):
        self.file_it()
        self.assertTrue(Notification.objects.filter(recipient=self.staff, verb__icontains="filed").exists())

    def test_J03_number_already_on_file_is_refused(self):
        self.doc()
        response = self.file_it(number=1)
        self.assertContains(response, "already on file")

    def test_J04_endorsement_needs_its_level(self):
        response = self.file_it(doc_type="IND")
        self.assertContains(response, "Say which endorsement")

    def test_J05_endorsement_number_carries_the_level(self):
        self.file_it(doc_type="IND", indorsement_level=2)
        filed = Document.objects.get(subject="Clean-up drive")
        self.assertTrue(filed.control_number.startswith("2nd ENDORSEMENT No. 001"), filed.control_number)

    def test_J06_series_year_up_to_next_year_only(self):
        next_year = date.today().year + 1
        self.assertEqual(self.file_it(series_year=next_year).status_code, 302)
        response = self.file_it(series_year=next_year + 1, subject="Too far ahead")
        self.assertContains(response, "between 1900 and next year")

    def test_J07_file_type_not_allowed_is_refused(self):
        response = self.file_it(file=SimpleUploadedFile("tool.exe", b"MZ....", "application/octet-stream"))
        self.assertContains(response, "Upload one of these file types")

    @override_settings(MAX_UPLOAD_SIZE=1024)
    def test_J08_file_over_the_size_limit_is_refused(self):
        response = self.file_it(file=SimpleUploadedFile("big.pdf", b"%PDF" + b"0" * 4096, "application/pdf"))
        self.assertContains(response, "larger than the")

    def test_J09_editing_without_a_new_file_keeps_the_file(self):
        # Cloudinary reports no size for stored files; simulate that here.
        document = self.doc_with_file("memo.pdf", pdf_bytes())
        stored = document.file.name
        self.client.force_login(self.admin)
        with patch("django.core.files.storage.FileSystemStorage.size", return_value=None):
            response = self.client.post(reverse("documents:document_update", args=[document.pk]),
                                        self.form_data(number=document.number, subject="Changed subject"))
        self.assertEqual(response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual((document.subject, document.file.name), ("Changed subject", stored))

    def test_J10_changing_the_number_on_edit(self):
        document = self.doc_with_file("memo.pdf", pdf_bytes())
        self.client.force_login(self.admin)
        with patch("django.core.files.storage.FileSystemStorage.size", return_value=None):
            self.client.post(reverse("documents:document_update", args=[document.pk]),
                             self.form_data(number=5, subject=document.subject))
        document.refresh_from_db()
        self.assertEqual(document.number, 5)

    def test_J11_removing_the_attached_file_on_edit(self):
        document = self.doc_with_file("memo.pdf", pdf_bytes())
        self.client.force_login(self.admin)
        self.client.post(reverse("documents:document_update", args=[document.pk]),
                         self.form_data(number=document.number, subject=document.subject, remove_file="on"))
        document.refresh_from_db()
        self.assertFalse(document.file)

    def test_J12_staff_cannot_file_or_edit(self):
        document = self.doc()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("documents:document_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("documents:document_update", args=[document.pk])).status_code, 403)

    def test_J13_super_admin_cannot_file_and_has_no_link(self):
        self.client.force_login(self.superadmin)
        self.assertEqual(self.client.get(reverse("documents:document_create")).status_code, 403)
        self.assertNotContains(self.client.get(reverse("documents:dashboard")),
                               f'href="{reverse("documents:document_create")}"')

    def test_J14_record_cannot_refer_to_itself(self):
        document = self.doc()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("documents:document_update", args=[document.pk]),
                                    self.form_data(number=document.number, subject=document.subject,
                                                   related_to=document.pk))
        self.assertContains(response, "cannot refer to itself")

    def test_J15_edits_are_logged_with_the_changed_fields(self):
        document = self.doc()
        self.client.force_login(self.admin)
        self.client.post(reverse("documents:document_update", args=[document.pk]),
                         self.form_data(number=document.number, subject="New wording"))
        entry = AccessLog.objects.filter(action=AccessLog.Action.UPDATE, document=document).first()
        self.assertIsNotNone(entry)
        self.assertIn("subject", entry.note)


# ---------------------------------------------------------------- M11
class M11_ViewingAndDownloading(Base):
    def test_K01_record_page_opens_and_is_logged(self):
        document = self.doc()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(document.get_absolute_url()).status_code, 200)
        self.assertTrue(AccessLog.objects.filter(action=AccessLog.Action.VIEW, document=document,
                                                 user=self.staff).exists())

    def test_K02_staff_cannot_open_an_internal_record(self):
        document = self.doc(classification=Document.Classification.INTERNAL)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(document.get_absolute_url()).status_code, 404)

    def test_K03_pdf_shows_in_the_viewer(self):
        document = self.doc_with_file("memo.pdf", pdf_bytes())
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_viewer", args=[document.pk]))
        self.assertContains(response, 'class="viewer-frame"')

    def test_K04_viewer_file_may_be_framed_by_the_site(self):
        document = self.doc_with_file("memo.pdf", pdf_bytes())
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_download", args=[document.pk]), {"view": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_K05_image_shows_as_a_picture(self):
        document = self.doc_with_file("scan.png", png_bytes())
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_viewer", args=[document.pk]))
        self.assertContains(response, 'class="viewer-image"')

    def test_K06_word_file_shows_as_a_page(self):
        document = self.doc_with_file("letter.docx", docx_bytes("Hello from the Word file"))
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_viewer", args=[document.pk]))
        self.assertContains(response, "viewer-page")
        self.assertContains(response, "Hello from the Word file")

    def test_K07_record_without_a_file_sends_you_back(self):
        document = self.doc()
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_viewer", args=[document.pk]))
        self.assertRedirects(response, document.get_absolute_url(), fetch_redirect_response=False)

    def test_K08_download_is_a_certified_pdf_and_is_logged(self):
        document = self.doc_with_file("memo.pdf", pdf_bytes())
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:document_download", args=[document.pk]))
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(AccessLog.objects.filter(action=AccessLog.Action.DOWNLOAD, document=document).exists())


# ---------------------------------------------------------------- M12
class M12_Enclosures(Base):
    def test_L01_admin_adds_an_enclosure(self):
        document = self.doc()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("documents:attachment_add", args=[document.pk]), {
            "label": "Annex A", "file": SimpleUploadedFile("annex.pdf", pdf_bytes(), "application/pdf")})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Attachment.objects.filter(document=document, label="Annex A").exists())

    def test_L02_enclosure_downloads(self):
        document = self.doc()
        attachment = Attachment(document=document, label="Annex A", uploaded_by=self.admin)
        attachment.file.save("annex.pdf", SimpleUploadedFile("annex.pdf", pdf_bytes()), save=True)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("documents:attachment_download", args=[attachment.pk]))
        self.assertEqual(response.status_code, 200)

    def test_L03_staff_cannot_add_an_enclosure(self):
        document = self.doc()
        self.client.force_login(self.staff)
        response = self.client.post(reverse("documents:attachment_add", args=[document.pk]), {
            "label": "X", "file": SimpleUploadedFile("x.pdf", pdf_bytes(), "application/pdf")})
        self.assertEqual(response.status_code, 404)

    def test_L04_staff_cannot_download_an_internal_records_enclosure(self):
        document = self.doc(classification=Document.Classification.INTERNAL)
        attachment = Attachment(document=document, label="Annex B", uploaded_by=self.admin)
        attachment.file.save("annex.pdf", SimpleUploadedFile("annex.pdf", pdf_bytes()), save=True)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("documents:attachment_download", args=[attachment.pk])).status_code, 404)


# ---------------------------------------------------------------- M13
class M13_RecycleBin(Base):
    def test_M01_removing_moves_to_the_bin_and_keeps_the_number(self):
        document = self.doc()
        self.client.force_login(self.admin)
        self.client.post(reverse("documents:document_delete", args=[document.pk]))
        document.refresh_from_db()
        self.assertTrue(document.is_deleted)
        self.assertEqual(document.number, 1)
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(reverse("documents:document_list"), {"q": "Budget"}),
                               "Budget hearing")

    def test_M02_bin_lists_removed_records(self):
        document = self.doc()
        document.soft_delete()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("documents:recycle_bin")), "Budget hearing")

    def test_M03_restore_brings_a_record_back(self):
        document = self.doc()
        document.soft_delete()
        self.client.force_login(self.admin)
        self.client.post(reverse("documents:document_restore", args=[document.pk]))
        document.refresh_from_db()
        self.assertFalse(document.is_deleted)
        self.assertTrue(AccessLog.objects.filter(action=AccessLog.Action.RESTORE, document=document).exists())

    def test_M04_staff_cannot_restore(self):
        document = self.doc()
        document.soft_delete()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(reverse("documents:document_restore", args=[document.pk])).status_code, 404)

    def test_M05_disposal_is_refused_inside_the_retention_period(self):
        document = self.doc()
        document.soft_delete()
        self.client.force_login(self.superadmin)
        self.client.post(reverse("documents:document_dispose", args=[document.pk]))
        self.assertTrue(Document.objects.filter(pk=document.pk).exists())

    def test_M06_super_admin_disposes_after_the_retention_period(self):
        document = self.doc()
        document.soft_delete()
        Document.objects.filter(pk=document.pk).update(
            deleted_at=timezone.now() - timedelta(days=settings.RECYCLE_BIN_RETENTION_DAYS + 1))
        self.client.force_login(self.superadmin)
        self.client.post(reverse("documents:document_dispose", args=[document.pk]))
        self.assertFalse(Document.objects.filter(pk=document.pk).exists())
        self.assertTrue(AccessLog.objects.filter(note__startswith="Disposed of").exists())

    def test_M07_administrator_cannot_dispose(self):
        document = self.doc()
        document.soft_delete()
        Document.objects.filter(pk=document.pk).update(
            deleted_at=timezone.now() - timedelta(days=settings.RECYCLE_BIN_RETENTION_DAYS + 1))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("documents:document_dispose", args=[document.pk])).status_code, 404)

    def test_M09_opening_the_restore_address_changes_nothing(self):
        document = self.doc()
        document.soft_delete()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("documents:document_restore", args=[document.pk]))
        self.assertRedirects(response, reverse("documents:recycle_bin"), fetch_redirect_response=False)
        document.refresh_from_db()
        self.assertTrue(document.is_deleted)

    def test_M10_restore_is_a_protected_form_button(self):
        document = self.doc()
        document.soft_delete()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("documents:recycle_bin"))
        self.assertContains(response, f'action="{reverse("documents:document_restore", args=[document.pk])}"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_M08_removed_number_is_never_reused(self):
        self.doc().soft_delete()
        self.client.force_login(self.admin)
        self.client.post(reverse("documents:document_create"), self.form_data())
        self.assertEqual(Document.objects.get(subject="Clean-up drive").number, 2)


# ---------------------------------------------------------------- M14
class M14_ExportAndAuditTrail(Base):
    def test_N01_csv_export_lists_the_records(self):
        self.doc()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("documents:export_csv"))
        self.assertEqual(response["Content-Type"], "text/csv")
        text = response.content.decode()
        self.assertIn("Control number", text)
        self.assertIn("Budget hearing schedule", text)

    def test_N02_csv_export_follows_the_search(self):
        self.doc()
        self.doc(subject="Fiesta preparations")
        self.client.force_login(self.admin)
        text = self.client.get(reverse("documents:export_csv"), {"q": "Fiesta"}).content.decode()
        self.assertIn("Fiesta preparations", text)
        self.assertNotIn("Budget hearing", text)

    def test_N03_staff_cannot_export(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("documents:export_csv")).status_code, 404)

    def test_N04_audit_trail_opens_and_filters_for_the_super_admin(self):
        AccessLog.objects.create(user=self.staff, action=AccessLog.Action.LOGIN)
        self.client.force_login(self.superadmin)
        response = self.client.get(reverse("documents:audit_trail"), {"action": "LOGIN"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "staff1")

    def test_N05_administrator_cannot_open_the_audit_trail(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("documents:audit_trail")).status_code, 403)


# ---------------------------------------------------------------- M15
class M15_FolderManagement(Base):
    def test_O01_folder_list_opens_for_administrators(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("documents:folder_list"))
        self.assertContains(response, "Memorandum")

    def test_O02_administrator_opens_a_new_folder(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("documents:folder_create"), {
            "label": "Resolution", "code": "RES", "long_name": "RESOLUTION", "icon": "icon-file-text", "tone": "slate"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("documents:document_create"))
        self.assertContains(response, "Resolution")

    def test_O03_every_field_of_a_new_folder_is_required(self):
        from documents.models import DocumentFolder

        self.client.force_login(self.admin)
        full = {"label": "Resolution", "code": "RES", "long_name": "RESOLUTION",
                "icon": "icon-file-text", "tone": "slate"}
        for name in full:
            response = self.client.post(reverse("documents:folder_create"), {**full, name: ""})
            self.assertContains(response, "This field is required", msg_prefix=name)
            # Only spaces counts as blank too.
            response = self.client.post(reverse("documents:folder_create"), {**full, name: "   "})
            self.assertEqual(response.status_code, 200, name)
        self.assertFalse(DocumentFolder.objects.filter(code="RES").exists())


# ---------------------------------------------------------------- M16
class M16_DjangoAdminSite(Base):
    def setUp(self):
        super().setUp()
        self.root = User.objects.create_superuser("root1", email="root1@example.com", password=PW)

    def test_P01_records_cannot_be_edited_or_deleted_in_django_admin(self):
        document = self.doc()
        self.client.force_login(self.root)
        self.assertEqual(self.client.get("/django-admin/documents/document/").status_code, 404)
        self.assertEqual(self.client.get(f"/django-admin/documents/document/{document.pk}/delete/").status_code, 404)
        self.assertTrue(Document.objects.filter(pk=document.pk).exists())

    def test_P02_audit_log_stays_read_only_in_django_admin(self):
        entry = AccessLog.objects.create(user=self.staff, action=AccessLog.Action.LOGIN)
        self.client.force_login(self.root)
        self.assertEqual(self.client.get("/django-admin/documents/accesslog/").status_code, 200)
        self.assertEqual(self.client.get(f"/django-admin/documents/accesslog/{entry.pk}/delete/").status_code, 403)
