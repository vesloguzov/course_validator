Сontents
========

* `User guide`_.
* `Installation`_.
* `Settings info`_.

User guide
==========
Введение
--------
Данное приложение предназначено для выполнения проверок курса.
Это может быть полезно сделать перед стартом курса для отлавливания различных нестыковок
или ошибочно выставленных настроек.
Проверка состоит из независимых тестов, каждый из которых инспектирует отдельные
пункты/настройки/данные курса и выводит полученные результаты. После выполнения проверки её результаты сохраняются на сервере, и в дальнейшем эти результаты
можно показать.


Выполнение новой проверки
-------------------------
Какие именно тесты будут выполняться при новой проверке, определяется в списке формы:

TODO: img списка чекбоксов

1. Выбрать в графе ``Action type`` пункт ``Proceed new validation`` TODO: img
2. Выбрать в графе ``Independent validations`` все интересующие тесты в `` . Некоторые из них отключены по умолчанию, так как могут занимать много времени.
3. Нажать ``Validate course``

Загрузка выполненной проверки
-----------------------------
1. Выбрать в графе ``Action type`` пункт ``Load previous validation``,
2. Выбрать одну из проведенных ранее проверок. Название проверки состоит из имени пользователя, проводившего проверку, и даты проведения.
3. Нажать ``Load Validation``

Описание отдельных тестов
-------------------------
1. Advanced Modules.

  | Выводит подключенные в курсе доболнительные XBlock (т.е. типы задач или другие элементы, не входящие в стандартный набор).
  | Тест никогда не проваливается

2. Cohorts.

  | Проверка включены ли в курсе когорты. Если да, то для каждой когорты вывод численности.
  | Тест проваливается, если когорты не включены.

3. Proctoring.

  | Проверка, есть ли в курсе наблюдаемые (proctored) экзамены.
  | Тест никогда не проваливается

4. Grade.

  | Проверка оценок. Включает в себя проверку следующих утверждений:
    1) Для каждой категории проверяемых задач (Домашние работы, Тесты и.т.д) количества задач, указанное в настройках, в точности совпадает с количеством задач в курсе.
    2) Сумма весов всех категорий проверяемых задач равна 100
    3) В курсе нет задач с категорией, не указанной в настройках
  | Если найдено хотя бы одно нарушение, тест проваливается, и в результатах указывается, где и в чем состоит нарушение.

5. Module

  | Анализ Разделов, Подразделов, Блоков и задач в курсе.
  | Состоит из двух частей:

  1) | Отдельный подсчет количества Разделов, Подразделов, Блоков, задач и видео в курсе. Вывод количества для каждого из типов.
      Все остальные элементы суммируются и выводятся как Others.

  2) | Для Разделов, Подразделов и Блоков делается проверка что:
     |   в Разделе есть хотя бы один Подраздел
     |   в Подразделе есть хотя бы один Блок
     |   в Блоке есть хотя бы один дочерний элемент

  | Если в пункте 2) найдено хотя бы одно нарушение, тест проваливается, и в результатах указывается, где и в чем состоит нарушение.

6. Video full

  | Внимание: возможна длительная проверка!
  | Проверка видео в курсе. Для каждого видео делается проверка, можно ли его посмотреть.
  | Вывод состоит из двух частей. В ``Видео кратко`` выводится информация о суммарной длине видео в каждом разделе.
  | В ``Видео целиком`` для каждого раздела выводится название каждого видео и его длительность (либо информация об ошибке), а также длительность видео в каждом разделе.
  | Если при получении информации о длительности хотя бы одного видео возникла ошибка, тест проваливается, и в результатах указывается, где и какая возникла ошибка.

7. Open Response Assessment

  Вывод информации по всем OpenResponseAssesment: даты старта/дедлайны, где находятся, какие шаги включены.
  | Тест никогда не проваливается.

8. Dates

  Проверка корректности дат старта Разделов, Подразделов и Блоков. Состоит из:

  1) Даты старта дочерних блоков больше дат старта блока-родителя

  2) Наличие блоков с датой старта меньше завтрашней даты

  3) Наличие среди стартующих не позднее завтра блоков видимых для студентов

  Если нарушается хотя бы одно из утверждений, тест проавливается, и в результатах указывается, где и в чем состоит ошибка.

9. Group

  | Для каждой группы из настроек вывод, используется ли она.
  | Тест никогда не проваливается.

10. Special exams

  | Вывод информации по всем "особым" экзаменам. Экзамен считается особым, если он ограничен по времени, либо указан как вступительный, либо является наблюдаемым (proctored), либо указан как practice exam.
  | Тест никогда не проваливается.

11. Response types

  | Попытка каждую задачу отнести к определенной категории (Численная задача, Множественный выбор, Текст и.т.д.). Для сторонних задач/XBlock задача может быть не отнесена ни к одной категории.
  | Если суммарное количество категоризированных задач меньше общего количества задач, тест проваливается.

12. Items visibility by group

  | Составляется таблица видимости элементов в каждой группе (обычный студент, verified и.т.д).
   Выводится число видимых каждой группой элементов среди Разделов, Подразделов, Блоков, Задач и Видео.
  | Тест никогда не проваливается.

Installation
============

1. - vagrant ssh
   - sudo su edxapp
   - cd /edx/app/edxapp/venvs/edxapp/src/
   - git clone https://github.com/zimka/edx-course-validator.git

2. ``python -m pip install /edx/app/edxapp/venvs/edxapp/src/edx-course-validator/``
3. ``nano /edx/app/edxapp/edx-platform/cms/envs/devstack.py``
    (or other environment.py): paste code at the end of file

  ::

    FEATURES["COURSE_VALIDATOR"] = True
    if FEATURES.get("COURSE_VALIDATOR"):
        INSTALLED_APPS += ("course_validator",)
        CV_PATH = REPO_ROOT.dirname() / "venvs" / "edxapp" / "src" / "edx-course-validator"/"course_validator"
        MAKO_TEMPLATES['main'] += (CV_PATH/"templates",)
        LOCALE_PATHS += (CV_PATH/"locale",)


  If you install course-validator in other directory, i.e. in /edx/app/edxapp/edx-platform/,
  replace 4th string: CV_PATH = REPO_ROOT.dirname() / "edx-platform" /"edx-course-validator"/"course_validator"

4. ``nano /edx/app/edxapp/edx-platform/cms/urls.py``
    paste code at the end of file

  ::

    if settings.FEATURES.get('COURSE_VALIDATOR'):
    urlpatterns += patterns(
        'course_validator.views',
        url(r'^check_course/{}/$'.format(settings.COURSE_KEY_PATTERN), 'course_validator_handler',
        name='course_validator_handler'),
    )

5. ``nano /edx/app/edxapp/edx-platform/cms/templates/widgets/header.html``

1) *Find next place (~125 string)*

    ::

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
            <a href="${reverse('export_git', kwargs=dict(course_key_string=unicode(course_key)))}">
              ${_("Export to Git")}
            </a>
          </li>
          % endif
        ------------------> Paste code from 5.2 here<--------------------------
        </ul>

2) *Paste next code in place that you found in 5.1:*

    ::

      % if settings.FEATURES.get("COURSE_VALIDATOR"):
        <%
           course_validator_url  = reverse('course_validator.views.course_validator_handler', kwargs={'course_key_string': unicode(course_key)})
        %>
        <li class="nav-item nav-course-tools-export">
          <a href="${course_validator_url}">${_("Validation")}</a>
        </li>
      % endif

6. Restart cms, check that new item "Validation" is in CMS > Some Course >  Tools

Settings info
=============

In edx-course-validator/course_validator/settings.py can be found global variables that define path where reports are saved and other validation settings.====
