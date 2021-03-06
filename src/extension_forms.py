# Copyright (c) 2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from urllib.parse import urlparse

from eolie.define import LOGINS
from eolie.helper_passwords import PasswordsHelper


class FormsExtension:
    """
        Handle forms prefill
    """

    def __init__(self, extension, settings):
        """
            Connect wanted signal
            @param extension as WebKit2WebExtension
            @param settings as Settings
        """
        self.__helper = PasswordsHelper()
        self.__settings = settings
        extension.connect("page-created", self.__on_page_created)

    def has_password(self, webpage):
        """
            True if webpage has a password input
        """
        dom_document = webpage.get_dom_document()
        inputs = dom_document.get_elements_by_tag_name("input")
        i = 0
        while i < inputs.get_length():
            if inputs.item(i).get_input_type() == "password":
                return True
            i += 1
        return False

    def get_input_forms(self, webpage):
        """
            Return forms for webpage
            @param webpage as WebKit2WebExtension.WebPage
            @return [WebKit2WebExtension.DOMHTMLInputElement]
        """
        forms = []
        dom_document = webpage.get_dom_document()
        inputs = dom_document.get_elements_by_tag_name("input")
        i = 0
        while i < inputs.get_length():
            if inputs.item(i).get_input_type() in ["text", "search"]:
                forms.append(inputs.item(i))
            i += 1
        return forms

    def get_textarea_forms(self, webpage):
        """
            Return forms for webpage
            @param webpage as WebKit2WebExtension.WebPage
            @return [WebKit2WebExtension.DOMHTMLInputElement]
        """
        forms = []
        dom_document = webpage.get_dom_document()
        textareas = dom_document.get_elements_by_tag_name("textarea")
        i = 0
        while i < textareas.get_length():
            forms.append(textareas.item(i))
            i += 1
        return forms

    def get_password_forms(self, name, webpage):
        """
            Return forms for webpage
            @param name as str
            @param webpage as WebKit2WebExtension.WebPage
            @return [WebKit2WebExtension.DOMHTMLInputElement]
        """
        forms = []
        dom_document = webpage.get_dom_document()
        inputs = dom_document.get_elements_by_tag_name("input")
        i = 0
        while i < inputs.get_length():
            if inputs.item(i).get_input_type() == "password" and\
                    (not name or name == inputs.item(i).get_attribute("name")):
                forms.append(inputs.item(i))
            i += 1
        return forms

    def get_login_forms(self, name, webpage):
        """
            Return auth forms for webpage
            @param name as str
            @param webpage as WebKit2WebExtension.WebPage
            @return [WebKit2WebExtension.DOMHTMLInputElement]
        """
        dom_document = webpage.get_dom_document()
        inputs = dom_document.get_elements_by_tag_name("input")
        i = 0
        forms = []
        while i < inputs.get_length():
            if inputs.item(i).get_input_type() == "text":
                input_name = inputs.item(i).get_attribute("name")
                input_id = inputs.item(i).get_attribute("id")
                # We search for wanted name
                if name and (name == input_name or name == input_id):
                    forms.append(inputs.item(i))
                else:
                    if self.is_login_form(inputs.item(i)):
                        forms.append(inputs.item(i))
            i += 1
        return forms

    def set_input_forms(self, attributes, password,
                        uri, index, count, webpage, username=None):
        """
            Set username/password input
            @param attributes as {}
            @param password as str
            @param uri as str
            @param index as int
            @param count as int
            @param webpage as WebKit2WebExtension.WebPage
            @param username as str/None
        """
        # We only set first available password
        if index != 0 and username is None:
            return
        parsed = urlparse(uri)
        # Allow unsecure completion if wanted by user
        if parsed.scheme != "https" and username is None:
            return
        submit_uri = "%s://%s" % (parsed.scheme, parsed.netloc)
        # Do not set anything if no attributes or
        # If we have already text in input and we are not a perfect completion
        if attributes is None or\
                (username is not None and attributes["login"] != username) or\
                attributes["formSubmitURL"] != submit_uri:
            return
        try:
            usernames = self.get_login_forms(attributes["userform"], webpage)
            passwords = self.get_password_forms(attributes["passform"],
                                                webpage)
            # Passwords form may have changed, take first
            if not passwords:
                passwords = self.get_password_forms("",
                                                    webpage)
            if usernames and passwords:
                usernames[0].set_value(attributes["login"])
                passwords[0].set_value(password)
        except Exception as e:
            print("FormsExtension::set_input_forms()", e)

    def is_login_form(self, form):
        """
            Return True if form is a login form
            @param form as WebKit2WebExtension.DOMHTMLInputElement
            @return bool
        """
        input_name = form.get_attribute("name")
        input_id = form.get_attribute("id")
        # We search for common name
        for search in LOGINS:
            if (input_name is not None and
                    input_name.lower().find(search) != -1) or\
                    (input_id is not None and
                        input_id.lower().find(search) != -1):
                return True
        return False

#######################
# PRIVATE             #
#######################
    def __on_page_created(self, extension, webpage):
        """
            Connect to send request
            @param extension as WebKit2WebExtension
            @param webpage as WebKit2WebExtension.WebPage
        """
        webpage.connect("document-loaded", self.__on_document_loaded)

    def __on_document_loaded(self, webpage):
        """
            Restore forms
            @param webpage as WebKit2WebExtension.WebPage
        """
        if not self.__settings.get_value("remember-passwords"):
            return
        if self.has_password(webpage):
            self.__helper.get(webpage.get_uri(),
                              self.set_input_forms,
                              webpage)
