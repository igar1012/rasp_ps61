from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
import pytz

URL = "https://www.altstu.ru/main/schedule/7000022513/"
TIMEZONE = pytz.timezone("Asia/Barnaul")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.9",
}


def clean_text(text):
  if not text:
    return ""
  return " ".join(text.replace("\xa0", " ").split()).strip()


def parse_schedule():
  response = requests.get(URL, headers=HEADERS, timeout=30)
  response.raise_for_status()
  response.encoding = "utf-8"

  soup = BeautifulSoup(response.text, "html.parser")
  cal = Calendar()
  cal.add("prodid", "-//AltSTU Schedule//RU")
  cal.add("version", "2.0")
  cal.add("x-wr-calname", "Расписание АлтГТУ (ПС-61)")
  cal.add("x-wr-timezone", "Asia/Barnaul")

  tables = soup.find_all("table")

  for table in tables:
    current_date = None
    rows = table.find_all("tr")

    for row in rows:
      # Заголовок дня (например: "01.09.2026 Вторник")
      day_th = row.find("th", class_="day")
      if day_th:
        day_text = clean_text(day_th.text)
        match = re.search(r"(\d{2}\.\d{2}\.\d{4})", day_text)
        if match:
          current_date = match.group(1)
        continue

      cells = row.find_all("td")
      if len(cells) >= 4 and current_date:
        time_slot = clean_text(cells[0].text)  # "09:55-11:25"
        subject = clean_text(cells[1].text)  # Предмет + подгруппа
        auditory = clean_text(cells[2].text)  # Ауд.
        teacher = clean_text(cells[3].text)  # Преподаватель

        time_match = re.search(r"(\d{2}):(\d{2})-(\d{2}):(\d{2})", time_slot)
        if not time_match:
          continue

        h_start, m_start, h_end, m_end = map(int, time_match.groups())
        day, month, year = map(int, current_date.split("."))

        dt_start = TIMEZONE.localize(
            datetime(year, month, day, h_start, m_start)
        )
        dt_end = TIMEZONE.localize(datetime(year, month, day, h_end, m_end))

        # Создаем событие
        event = Event()
        event.add("summary", subject)
        event.add("dtstart", dt_start)
        event.add("dtend", dt_end)
        if auditory:
          event.add("location", auditory)

        description = []
        if teacher:
          description.append(f"Преподаватель: {teacher}")
        if auditory:
          description.append(f"Аудитория: {auditory}")
        event.add("description", "\n".join(description))

        # Уникальный идентификатор события
        uid = f"{year}{month:02d}{day:02d}T{h_start:02d}{m_start:02d}_{abs(hash(subject + auditory))}@altstu"
        event.add("uid", uid)

        cal.add_component(event)

  with open("schedule.ics", "wb") as f:
    f.write(cal.to_ical())
  print("Календарь успешно обновлен и сохранен в schedule.ics")


if __name__ == "__main__":
  parse_schedule()