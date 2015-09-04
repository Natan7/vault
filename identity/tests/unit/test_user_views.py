# -*- coding:utf-8 -*-

# from django import forms
from unittest import TestCase
from mock import Mock, patch

from vault.tests.fakes import fake_request
from identity.tests.fakes import FakeResource, FakeToken
from identity.views import (ListUserView, CreateUserView, UpdateUserView,
                            DeleteUserView, UpdateProjectUserPasswordView)


class ListUserTest(TestCase):

    def setUp(self):
        self.view = ListUserView.as_view()

        self.request = fake_request(method='GET')
        self.request.user.is_superuser = True

        patch('identity.keystone.Keystone._keystone_conn',
              Mock(return_value=None)).start()

    def tearDown(self):
        patch.stopall()

    def test_list_users_needs_authentication(self):
        self.request.user.is_authenticated = lambda: False
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)

    def test_show_user_list(self):
        patch('identity.keystone.Keystone.user_list',
              Mock(return_value=[FakeResource(1)])).start()

        self.request.user.is_authenticated = lambda: True
        self.request.user.token = FakeToken

        response = self.view(self.request)

        response.render()

        self.assertIn('<td>FakeResource1</td>', response.content)

    @patch('identity.keystone.Keystone.user_list')
    def test_list_user_view_exception(self, mock_user_list):
        mock_user_list.side_effect = Exception()

        self.request.user.is_authenticated = lambda: True
        self.request.user.token = FakeToken

        response = self.view(self.request)
        msgs = [msg for msg in self.request._messages]

        self.assertGreater(len(msgs), 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(msgs[0].message, 'Unable to list users')


class CreateUserTest(TestCase):

    def setUp(self):
        self.view = CreateUserView.as_view()

        self.request = fake_request()
        self.request.META.update({
            'SERVER_NAME': 'globo.com',
            'SERVER_PORT': '80'
        })
        self.request.user.is_superuser = True
        self.request.user.is_authenticated = lambda: True
        self.request.user.token = FakeToken

        patch('actionlogger.ActionLogger.log',
              Mock(return_value=None)).start()

        patch('identity.keystone.Keystone._keystone_conn',
              Mock(return_value=None)).start()

        patch('identity.keystone.Keystone.project_list',
              Mock(return_value=[FakeResource(1, 'project1')])).start()

        patch('identity.keystone.Keystone.role_list',
              Mock(return_value=[FakeResource(1, 'role1')])).start()

    def tearDown(self):
        patch.stopall()

    def test_create_user_needs_authentication(self):
        self.request.user.is_authenticated = lambda: False
        self.request.user.token = None

        response = self.view(self.request)

        self.assertEqual(response.status_code, 302)

    def test_ensure_project_list_was_filled_up(self):
        response = self.view(self.request)
        response.render()

        self.assertIn('<option value="1">project1</option>', response.content)

    def test_ensure_role_list_was_filled_up(self):
        response = self.view(self.request)
        response.render()

        self.assertIn('<option value="1">role1</option>', response.content)

    def test_enabled_field_is_a_select_tag(self):
        from django.forms.widgets import Select
        enabled_field = CreateUserView.form_class.base_fields['enabled']

        self.assertIsInstance(enabled_field.widget, Select)

    def test_ensure_enabled_field_initial_value_is_true(self):
        enabled_field = CreateUserView.form_class.base_fields['enabled']

        self.assertTrue(enabled_field)

    def test_validating_a_blank_field(self):
        user = FakeResource(1, 'user1')
        user.to_dict = lambda: {'name': user.name}
        user.default_project_id = 1
        user.project_id = 1

        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=user)).start()

        self.request.method = 'POST'

        post = self.request.POST.copy()
        post.update({'name': '', 'enabled': True, 'id': 1, 'project': 1,
            'role': 1, 'password': 'aaa', 'password_confirm': 'aaa',
            'email': 'a@a.net'})
        self.request.POST = post

        response = self.view(self.request)
        response.render()

        self.assertIn('This field is required', response.content)

    def test_validating_email_field(self):
        user = FakeResource(1, 'user1')
        user.to_dict = lambda: {'name': user.name}
        user.default_project_id = 1
        user.project_id = 1

        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=user)).start()

        self.request.method = 'POST'

        post = self.request.POST.copy()
        post.update({'name': 'aaa', 'enabled': True, 'id': 1, 'project': 1,
            'role': 1, 'password': 'aaa', 'password_confirm': 'aaa',
            'email': 'a.a.net'})
        self.request.POST = post

        response = self.view(self.request)
        response.render()

        self.assertIn('Enter a valid email address', response.content)

    @patch('identity.keystone.Keystone.user_create')
    def test_user_create_method_was_called(self, mock):

        self.request.method = 'POST'
        post = self.request.POST.copy()
        post.update({'name': 'aaa', 'enabled': True, 'id': 1, 'project': 1,
                     'role': 1, 'password': 'aaa', 'password_confirm': 'aaa',
                     'email': 'a@a.net'})
        self.request.POST = post

        response = self.view(self.request)

        mock.assert_called_with(name='aaa', enabled=True,
            project_id=1, role_id=1, password='aaa', email='a@a.net', domain=None)

    @patch('identity.keystone.Keystone.user_create')
    def test_create_user_view_exception(self, mock_user_create):
        mock_user_create.side_effect = Exception()

        self.request.method = 'POST'
        post = self.request.POST.copy()
        post.update({'name': 'aaa', 'enabled': True, 'id': 1, 'project': 1,
                     'role': 1, 'password': 'aaa', 'password_confirm': 'aaa',
                     'email': 'a@a.net'})
        self.request.POST = post

        response = self.view(self.request)
        msgs = [msg for msg in self.request._messages]

        self.assertGreater(len(msgs), 0)
        self.assertEqual(msgs[0].message, 'Error when create user')


class UpdateUserTest(TestCase):

    def setUp(self):
        self.view = UpdateUserView.as_view()

        self.request = fake_request()
        self.request.META.update({
            'SERVER_NAME': 'globo.com',
            'SERVER_PORT': '80'
        })
        self.request.user.is_superuser = True
        self.request.user.is_authenticated = lambda: True
        self.request.user.token = FakeToken

        patch('actionlogger.ActionLogger.log',
              Mock(return_value=None)).start()

        patch('identity.keystone.Keystone._keystone_conn',
              Mock(return_value=None)).start()

    def tearDown(self):
        patch.stopall()

    def test_update_user_needs_authentication(self):
        self.request.user.is_authenticated = lambda: False
        self.request.user.token = None

        response = self.view(self.request)

        self.assertEqual(response.status_code, 302)

    @patch('identity.keystone.Keystone.user_update')
    def test_user_update_method_was_called(self, mock_user_update):

        patch('identity.keystone.Keystone.project_list',
            Mock(return_value=[FakeResource(1, 'project1')])).start()

        patch('identity.keystone.Keystone.project_get',
            Mock(return_value=1)).start()

        user = FakeResource(1, 'user1')
        user.to_dict = lambda: {'name': user.name}
        user.project_id = 1

        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=user)).start()

        project = FakeResource(1, 'project1')
        project.to_dict = lambda: {'name': project.name}
        patch('identity.keystone.Keystone.project_get',
              Mock(return_value=project)).start()

        self.request.method = 'POST'

        post = self.request.POST.copy()
        post.update({'id': 1, 'name': 'aaa', 'project': 1})
        self.request.POST = post

        response = self.view(self.request)

        mock_user_update.assert_called_with(user, name='aaa', project=project,
                                            domain=None, enabled=True,
                                            password=None, email=None)

    @patch('identity.keystone.Keystone.user_update')
    def test_update_user_view_exception(self, mock_user_update):
        mock_user_update.side_effect = Exception()

        patch('identity.keystone.Keystone.project_list',
            Mock(return_value=[FakeResource(1, 'project1')])).start()

        patch('identity.keystone.Keystone.project_get',
            Mock(return_value=1)).start()

        user = FakeResource(1, 'user1')
        user.to_dict = lambda: {'name': user.name}
        user.default_project_id = 1

        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=user)).start()

        self.request.method = 'POST'
        post = self.request.POST.copy()
        post.update({'id': 1, 'name': 'aaa', 'project': 1})
        self.request.POST = post

        response = self.view(self.request)
        msgs = [msg for msg in self.request._messages]

        self.assertGreater(len(msgs), 0)
        self.assertEqual(msgs[0].message, 'Error when update user')

    @patch('identity.keystone.Keystone.user_update')
    def test_update_user_change_password_exception(self, mock_user_update):
        mock_user_update.side_effect = Exception()

        patch('identity.keystone.Keystone.project_list',
            Mock(return_value=[FakeResource(1, 'project1')])).start()

        patch('identity.keystone.Keystone.project_get',
            Mock(return_value=1)).start()

        user = FakeResource(1, 'user1')
        user.to_dict = lambda: {'name': user.name}
        user.default_project_id = 1

        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=user)).start()

        self.request.method = 'POST'
        post = self.request.POST.copy()
        post.update({
            'id': 1,
            'name': 'aaa',
            'project': 1,
            'password': 'globo123',
            'password_confirm': 'globo',
        })
        self.request.POST = post

        response = self.view(self.request)
        msgs = [msg for msg in self.request._messages]

        self.assertIn('Passwords did not match', response.rendered_content)
        self.assertEqual(len(msgs), 0)


class DeleteUserTest(TestCase):

    def setUp(self):
        self.view = DeleteUserView.as_view()

        self.request = fake_request()
        self.request.META.update({
            'SERVER_NAME': 'globo.com',
            'SERVER_PORT': '80'
        })
        self.request.user.is_superuser = True
        self.request.user.is_authenticated = lambda: True
        self.request.user.token = FakeToken

        patch('actionlogger.ActionLogger.log',
              Mock(return_value=None)).start()

        patch('identity.keystone.Keystone._keystone_conn',
              Mock(return_value=None)).start()

    def tearDown(self):
        patch.stopall()

    def test_delete_user_needs_authentication(self):
        self.request.user.is_authenticated = lambda: False
        self.request.user.token = None

        response = self.view(self.request)

        self.assertEqual(response.status_code, 302)

    @patch('identity.keystone.Keystone.user_delete')
    def test_user_delete_method_was_called(self, mock_user_delete):
        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=FakeResource(1, 'user1'))).start()

        response = self.view(self.request, user_id=1)

        mock_user_delete.assert_called_with(1)

    @patch('identity.keystone.Keystone.user_delete')
    def test_user_delete_sucessfull_message(self, mock_user_delete):
        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=FakeResource(1, 'user1'))).start()

        response = self.view(self.request, user_id=1)
        msgs = [msg for msg in self.request._messages]

        self.assertGreater(len(msgs), 0)
        self.assertEqual(msgs[0].message, 'Successfully deleted user')

    @patch('identity.keystone.Keystone.user_delete')
    def test_user_delete_view_exception(self, mock_user_delete):
        mock_user_delete.side_effect = Exception()

        patch('identity.keystone.Keystone.user_get',
              Mock(return_value=FakeResource(1, 'user1'))).start()

        response = self.view(self.request, user_id=1)
        msgs = [msg for msg in self.request._messages]

        self.assertGreater(len(msgs), 0)
        self.assertEqual(msgs[0].message, 'Error when delete user')


class UpdateProjectUserPasswordTest(TestCase):

    def setUp(self):
        self.view = UpdateProjectUserPasswordView.as_view()

        self.request = fake_request(method='GET')
        self.request.user.is_superuser = True

        self.mock_keystone_find_user = patch('identity.keystone.Keystone.return_find_u_user').start()
        # Retorna objeto usuário similar ao do request
        self.mock_keystone_find_user.return_value = fake_request(method='GET').user

        self.mock_users_list = patch('identity.keystone.Keystone.user_list').start()
        self.mock_users_list.return_value = [fake_request(method='GET').user]

        patch('identity.keystone.Keystone._keystone_conn',
              Mock(return_value=None)).start()

    def tearDown(self):
        patch.stopall()

    def test_reset_password_needs_authentication(self):
        self.request.user.is_authenticated = lambda: False
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)

    @patch('identity.keystone.Keystone.return_find_u_user')
    def test_return_find_u_user_was_called(self, mock_find_user):
        self.request.user.is_authenticated = lambda: True

        self.view(self.request)

        mock_find_user.assert_called_with(None)

    @patch('identity.keystone.Keystone.create_password')
    def test_create_password_was_called(self, mock_create_password):
        self.request.user.is_authenticated = lambda: True

        self.view(self.request)

        mock_create_password.assert_called_with()

    @patch('identity.keystone.Keystone.user_update')
    def test_user_update_was_called(self, mock_user_update):
        self.request.user.is_authenticated = lambda: True
        password = 'B52j7#ZDYuyS'

        patch('identity.keystone.Keystone.create_password',
              Mock(return_value=password)).start()

        self.view(self.request)

        mock_user_update.assert_called_with(self.request.user, password=password)

    @patch('identity.keystone.Keystone.return_find_u_user')
    def test_return_find_u_user_with_exception(self, mock_find_u_user):
        self.request.user.is_authenticated = lambda: True
        mock_find_u_user.side_effect = Exception()

        response = self.view(self.request)

        self.assertEqual('{}', response.content)
        self.assertEqual(response.status_code, 200)

    @patch('identity.keystone.Keystone.return_find_u_user')
    def test_return_user_update_with_exception(self, mock_user_update):
        self.request.user.is_authenticated = lambda: True
        mock_user_update.side_effect = Exception()

        response = self.view(self.request)

        self.assertEqual('{}', response.content)
        self.assertEqual(response.status_code, 200)

    @patch('identity.keystone.Keystone.user_update')
    def test_return_reset_password_with_new_password(self, mock_user_update):
        self.request.user.is_authenticated = lambda: True
        password = 'B52j7#ZDYuyS'

        patch('identity.keystone.Keystone.create_password',
              Mock(return_value=password)).start()

        response = self.view(self.request)

        mock_user_update.assert_called_with(self.request.user, password=password)
        self.assertIn(password, response.content)
        self.assertEqual(response.status_code, 200)
