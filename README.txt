Installation
0)  vagrant ssh
    sudo su edxapp
    mkdir /edx/app/edxapp/venv/edxapp/src/edx-course-validator
    cd /edx/app/edxapp/venv/edxapp/src/edx-course-validator
    git clone https://github.com/zimka/course_validator.git

1) pip install -e .
2) edx-platform/cms/envs/(some environment file, e.g. 'devstack').py: paste code at the end of file

FEATURES["COURSE_VALIDATOR"] = True
if FEATURES.get("COURSE_VALIDATOR"):
    INSTALLED_APPS +=("course_validator",)
    LOCALE_PATHS += ('/edx/app/edxapp/venvs/edxapp/src/edx_course_validator/course_validator/locale',)
    CV_PATH = REPO_ROOT.dirname() /"venvs"/"edxapp"/"src"/"edx_course_validator"
    MAKO_TEMPLATES['main'] += CV_PATH/"course_validator"/"templates",
    LOCALE_PATHS += (CV_PATH/"course_validator"/"locale",)

3) edx-platform/cms/urls.py: paste code at the end of file

if settings.FEATURES.get('COURSE_VALIDATOR'):
    urlpatterns += patterns(
        'course_validator.views',
        url(r'^check_course/{}/$'.format(settings.COURSE_KEY_PATTERN), 'course_validator_handler',
        name='course_validator_handler'),
    )

4) Find edx-platform/cms/templates/widgets/header.html:
    4.1) Find place (~125 string):
              <div class="nav-sub">
                <ul>
                  <li class="nav-item nav-course-tools-checklists">
                    <a href="${checklists_url}">${_("Checklists")}</a>
                  </li>
                  <li class="nav-item nav-course-tools-import">
                    <a href="${import_url}">${_("Import")}</a>
                  </li>
                  <li class="nav-item nav-course-tools-export">
                    <a href="${export_url}">${_("Export")}</a>
                  </li>
                  % if settings.FEATURES.get('ENABLE_EXPORT_GIT') and context_course.giturl:
                  <li class="nav-item nav-course-tools-export-git">
                    <a href="${reverse('export_git', kwargs=dict(course_key_string=unicode(course_key)))}">${_("Export to Git")}</a>
                  </li>
                  % endif
    ------------------> Paste code from 4.2 here<--------------------------
                </ul>

    4.2) Past next code in place that you found in 4.1:

    % if settings.FEATURES.get("COURSE_VALIDATOR"):
     <%
      course_validator_url  = reverse('course_validator.views.course_validator_handler', kwargs={'course_key_string': unicode(course_key)})
      %>
      <li class="nav-item nav-course-tools-export">
        <a href="${course_validator_url}">${_("Validation")}</a>
      </li>
    % endif