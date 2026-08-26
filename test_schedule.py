from datetime import date

from schedule import ALTERNATE, BUSY, DAY, NIGHT, OFF, Person, kind

ANCHOR = date(2026, 8, 12)  # среда, первая смена цикла


def p(**kw):
    base = dict(id=1, name="Егор", cycle_on=2, cycle_off=2, anchor=ANCHOR, mode=DAY)
    return Person(**{**base, **kw})


def test_cycle_2_2_дневной_режим():
    person = p()
    assert kind(person, date(2026, 8, 12), {}) == DAY    # 1-я смена
    assert kind(person, date(2026, 8, 13), {}) == DAY    # 2-я смена
    assert kind(person, date(2026, 8, 14), {}) == OFF    # выходной
    assert kind(person, date(2026, 8, 15), {}) == OFF    # выходной
    assert kind(person, date(2026, 8, 16), {}) == DAY    # цикл пошёл заново


def test_ночной_режим_всегда_ночь():
    person = p(mode=NIGHT)
    assert kind(person, date(2026, 8, 12), {}) == NIGHT
    assert kind(person, date(2026, 8, 14), {}) == OFF


def test_чередование_день_ночь_по_блокам():
    person = p(mode=ALTERNATE)
    assert kind(person, date(2026, 8, 12), {}) == DAY     # блок 0
    assert kind(person, date(2026, 8, 13), {}) == DAY
    assert kind(person, date(2026, 8, 16), {}) == NIGHT   # блок 1
    assert kind(person, date(2026, 8, 17), {}) == NIGHT
    assert kind(person, date(2026, 8, 20), {}) == DAY     # блок 2


def test_даты_раньше_якоря_разворачиваются_назад():
    person = p(mode=ALTERNATE)
    assert kind(person, date(2026, 8, 11), {}) == OFF     # выходной перед якорем
    assert kind(person, date(2026, 8, 10), {}) == OFF
    assert kind(person, date(2026, 8, 9), {}) == NIGHT    # предыдущий блок
    assert kind(person, date(2026, 8, 8), {}) == NIGHT


def test_нечётный_цикл_3_3():
    person = p(cycle_on=3, cycle_off=3)
    assert kind(person, date(2026, 8, 14), {}) == DAY     # 3-я смена
    assert kind(person, date(2026, 8, 15), {}) == OFF
    assert kind(person, date(2026, 8, 18), {}) == DAY     # цикл заново


def test_правка_перекрывает_паттерн():
    person = p()
    overrides = {date(2026, 8, 12): OFF, date(2026, 8, 14): BUSY}
    assert kind(person, date(2026, 8, 12), overrides) == OFF
    assert kind(person, date(2026, 8, 14), overrides) == BUSY
    assert kind(person, date(2026, 8, 13), overrides) == DAY  # соседние дни не тронуты
