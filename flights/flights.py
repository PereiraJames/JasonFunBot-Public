import os
import re
import csv
from pathlib import Path
import json
from typing import Optional, Dict, Any, List, Tuple
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import pdfplumber
import airportsdata
from zoneinfo import ZoneInfo
import hashlib

SG_TZ = timezone(timedelta(hours=8))

AIRPORTS = airportsdata.load()

SGT = ZoneInfo("Asia/Singapore")

load_dotenv()

db_config = json.loads(os.getenv("DB_CONFIG"))

FLIGHTS_DATABASE = "flights"

async def save_raw_pdf_telegram(update, context):
    msg = update.message

    if not msg or not msg.document:
        await msg.reply_text("No document received.")
        return

    # Only accept PDFs (optional but recommended)
    if msg.document.mime_type != "application/pdf":
        await msg.reply_text("Please upload a PDF file.")
        return

    os.makedirs("flights-pdf", exist_ok=True)

    tg_file = await msg.document.get_file()
    filename = "flights-pdf/report.pdf"
    await tg_file.download_to_drive(custom_path=filename)

    print(f"Saved PDF: {filename}")

    extracted_flights = extract_table(filename)

    file_hash = hash_file_contents(filename)

    # FIX: if it's already in DB, then stop
    if check_hash_in_database(file_hash):
        await msg.reply_text("This roster was already uploaded.")
        return

    # FIX: pass the real hash
    update_flight_database(extracted_flights, file_hash)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Successfully uploaded the new roster."
    )

def convertToSGT(foreignTime: str, foreignStation: str) -> str | None:
    if not foreignTime or not foreignStation:
        return None

    tz_name = get_timezone_from_iata(foreignStation)
    if not tz_name:
        raise ValueError(f"Timezone not found for {foreignStation}")

    foreign_tz = ZoneInfo(tz_name)
    sgt_tz = ZoneInfo("Asia/Singapore")

    # Parse "HHMM ddMonyy"
    dt = datetime.strptime(foreignTime.strip(), "%H%M %d%b%y")

    # Attach foreign timezone
    dt = dt.replace(tzinfo=foreign_tz)

    # Convert to Singapore time
    dt_sgt = dt.astimezone(sgt_tz)

    #print(f"Converted from {foreignTime} to {dt_sgt.strftime("%H%M %d%b%y")} | {foreignStation}")

    return dt_sgt.strftime("%H%M %d%b%y")

def get_timezone_from_iata(iata: str) -> str | None:
    iata = iata.strip().upper()
    for airport in AIRPORTS.values():
        if airport.get("iata") == iata:
            return airport.get("tz")
    return None


def extract_table(flight_file="flights-pdf\\report.pdf"):
    
    flight_tables = []
    

    with pdfplumber.open(flight_file) as pdf:
        page = pdf.pages[0]
        flight_details = page.extract_table()
        

    for index, flight_detail in enumerate(flight_details[1:], start=1):

        date = flight_detail[0]
        flightNo = flight_detail[2]
        sector = flight_detail[3]
        aircraft = flight_detail[4]
        duty = flight_detail[5]
        reportingTime = flight_detail[8]
        departTime = flight_detail[9]
        arrivalTime = flight_detail[10]
        
        
        if "-" in flight_detail[3]:
            if flight_detail[10]=="" or flight_detail[9]=="":
            #compare to previous flight detail
                if index > 0:
                    if flight_details[index - 1][2] == flightNo:
                        previousFlight = flight_details[index - 1]

                        if previousFlight[9] != "":
                            flight_detail[9] = previousFlight[9]
                            departTime = flight_detail[9]

                        
                        if previousFlight[10] != "":
                            flight_detail[10] = previousFlight[10]
                            arrivalTime = flight_detail[10]

                if index + 1 < len(flight_details):
                    if flight_details[index + 1][2] == flightNo:
                        nextFlight = flight_details[index + 1]

                        if nextFlight[9] != "":
                            flight_detail[9] = nextFlight[9]
                            departTime = flight_detail[9]
                        
                        if nextFlight[10] != "":
                            flight_detail[10] = nextFlight[10]
                            arrivalTime = flight_detail[10]
                

        #If date is empty copy the date of the previous entry
        if date == "" and index > 0:
            flight_detail[0] = flight_details[index - 1][0]
            date = flight_detail[0]
        
        #Sets the timings to hhmm ddMonyy - 1535 12Jan26
        if reportingTime:
            reportingTime = f"{flight_detail[8]} {date}"

        if departTime:
            departTime = f"{flight_detail[9]} {date}"

        if arrivalTime:
            arrivalTime = f"{flight_detail[10]} {date}"

        flightLength = calc_flight_length(departTime, arrivalTime)

        def normalize(value):
            value = (value or "").strip()
            return value if value else "NA"


        flight = {
            "date": normalize(date),
            "flightNo": normalize(flightNo),
            "sector": normalize(sector),
            "aircraft": normalize(aircraft),
            "duty": normalize(duty),
            "reportingTime": normalize(reportingTime),
            "departTime": normalize(departTime),
            "arrivalTime": normalize(arrivalTime),
            "flightLength": normalize(flightLength),
            "date_lookup": to_lookup_date(date),
            "departure_lookup": to_lookup_datetime(departTime),
            "arrival_lookup": to_lookup_datetime(arrivalTime)
        }

        flight_tables.append(flight)
    
    return flight_tables

def to_lookup_date(ddMonyy: str) -> str:
    """
    Converts '29Jan26' -> '2026-01-29'
    Returns 'NA' if invalid.
    """
    try:
        dt = datetime.strptime(ddMonyy.strip(), "%d%b%y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "NA"
    
def to_lookup_datetime(hhmm_ddMonyy: str) -> str:
    """
    Converts '1205 29Jan26' -> '2026-01-29 12:05:00'
    """
    try:
        dt = datetime.strptime(hhmm_ddMonyy.strip(), "%H%M %d%b%y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "NA"

def check_hash_in_database(hash_value: str) -> bool:
    """
    Returns True if hash already exists in database.
    Returns False if hash does NOT exist (new file).
    """

    sql = f"""
        SELECT 1
        FROM {FLIGHTS_DATABASE}
        WHERE reportHash = %s
        LIMIT 1
    """

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    try:
        cursor.execute(sql, (hash_value,))
        result = cursor.fetchone()

        return result is not None

    finally:
        cursor.close()
        db.close()

def hash_file_contents(filename: str) -> str:
    sha256 = hashlib.sha256()

    with open(filename, "rb") as f:
        # Read in chunks to handle large files safely
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)

    print(f"Successfully hashed | {sha256.hexdigest()}")

    return sha256.hexdigest()

def now_sg_date_str():
    return datetime.now(SG_TZ).date().isoformat()

def parse_hhmm(t: str) -> datetime:
    """
    Accepts '0720' or '07:20' and returns a datetime (date part is dummy).
    """
    t = (t or "").strip()
    if not t:
        raise ValueError("Empty time")

    if ":" in t:
        hh, mm = t.split(":")
    else:
        hh, mm = t[:2], t[2:4]

    return datetime(2000, 1, 1, int(hh), int(mm))

def calc_flight_length(dep: str, arr: str) -> str | None:
    dep = (dep or "").strip()
    arr = (arr or "").strip()

    if not dep or not arr:
        return None

    try:
        d = parse_hhmm(dep)
        a = parse_hhmm(arr)
    except ValueError:
        return None

    if a < d:
        a += timedelta(days=1)

    delta = a - d
    mins = int(delta.total_seconds() // 60)

    hours = mins // 60
    minutes = mins % 60

    if hours == 0:
        return f"{minutes}mins"
    if minutes == 0:
        return f"{hours}hrs"
    return f"{hours}hrs{minutes}mins"

def update_flight_database(flight_details: list[dict], reportHash: str = "a"):
    insert_sql = f"""
    INSERT INTO {FLIGHTS_DATABASE}
    (date, flightNo, sector, aircraft, duty,
     reportingTime, departureTime, arrivalTime,
     flightLength, reportHash, date_lookup, departure_lookup, arrival_lookup)
    VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s ,%s , %s)
    """

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    def na_to_none(v):
        v = (v or "").strip()
        return None if v in ("", "NA", "-") else v

    try:
        for flight in flight_details:
            cursor.execute(insert_sql, (
                na_to_none(flight.get("date")),
                na_to_none(flight.get("flightNo")),
                na_to_none(flight.get("sector")),
                na_to_none(flight.get("aircraft")),
                na_to_none(flight.get("duty")),
                na_to_none(flight.get("reportingTime")),
                na_to_none(flight.get("departTime")),
                na_to_none(flight.get("arrivalTime")),
                na_to_none(flight.get("flightLength")),  # if this is minutes, store int instead
                reportHash,
                na_to_none(flight.get("date_lookup")),
                na_to_none(flight.get("departure_lookup")),
                na_to_none(flight.get("arrival_lookup")),
            ))
        db.commit()
    finally:
        cursor.close()
        db.close()


def _today_ddMonyy() -> str:
    return datetime.now(SGT).strftime("%d%b%y")  # e.g. "29Jan26"

async def current_flight_details(update, context) -> list[dict]:
    """All roster rows for today's date (SGT), ordered nicely."""
    today = _today_ddMonyy()

    sql = """
    SELECT id, date, flightNo, sector, aircraft, duty,
           reportingTime, departureTime, arrivalTime, flightLength, created_at
    FROM flights
    WHERE date = %s
    ORDER BY
      CASE duty WHEN 'FLY' THEN 0 WHEN 'SN60' THEN 1 WHEN 'LO' THEN 2 ELSE 3 END,
      STR_TO_DATE(departureTime, '%H%i %d%b%y')
    """

    db = mysql.connector.connect(**db_config)
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(sql, (today,))
        rows = cur.fetchall()

        if not rows:
            text = f"```\nNo roster entries available for {today}.\n```"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode="Markdown"
            )
            return

        lines = []
        lines.append(f"ROSTER INFORMATION - {today}")
        lines.append("-" * 50)

        for r in rows:
            duty = r.get("duty") or "NA"
            sector = r.get("sector") or "NA"
            flight_no = r.get("flightNo") or "NA"
            dep = r.get("departureTime") or "NA"
            arr = r.get("arrivalTime") or "NA"
            duration = r.get("flightLength") or "NA"

            if duty == "FLY":
                lines.append(f"{flight_no:<7} {sector}")
                lines.append(f"DEP {dep:<15}")
                lines.append(f"ARR {arr:<15}")
                lines.append(f"DURATION {duration}")
                lines.append("")
            else:
                lines.append(f"{duty:<7} {sector}")
                lines.append("")

        lines.append("-" * 50)

        text = "```\n" + "\n".join(lines) + "\n```"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="Markdown"
        )

        return

    finally:
        cur.close()
        db.close()


async def next_flight_details(update, context):

    sql = """
        SELECT *
        FROM flights
        WHERE duty = 'FLY'
          AND departure_lookup >= NOW()
        ORDER BY departure_lookup
        LIMIT 2
    """

    db = mysql.connector.connect(**db_config)
    cur = db.cursor(dictionary=True)

    try:
        cur.execute(sql)
        rows = cur.fetchall()

        if not rows:
            text = "```\nNo further flights available.\nPlease update database.\n```"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode="Markdown"
            )
            return

        lines = []
        lines.append("NEXT SCHEDULED FLIGHTS")
        lines.append("-" * 50)

        for idx, r in enumerate(rows, start=1):
            lines.append(f"FLIGHT {idx}")
            lines.append(f"{'Date':<16}: {r.get('date') or 'NA'}")
            lines.append(f"{'Flight Number':<16}: {r.get('flightNo') or 'NA'}")
            lines.append(f"{'Sector':<16}: {r.get('sector') or 'NA'}")
            lines.append(f"{'Aircraft':<16}: {r.get('aircraft') or 'NA'}")
            lines.append(f"{'Reporting Time':<16}: {r.get('reportingTime') or 'NA'}")
            lines.append(f"{'Departure Time':<16}: {r.get('departureTime') or 'NA'}")
            lines.append(f"{'Arrival Time':<16}: {r.get('arrivalTime') or 'NA'}")
            lines.append(f"{'Flight Duration':<16}: {r.get('flightLength') or 'NA'}")
            lines.append("-" * 50)

        text = "```\n" + "\n".join(lines) + "\n```"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="Markdown"
        )

    finally:
        cur.close()
        db.close()



if __name__ == "__main__":
    # --- Local test config ---
    # Put your PDFs + generated CSVs in this folder:
    #convert_raw_to_clean_csv(CHAT_RESPONSE)
    all_flight_details = extract_table()

    #update_flight_database(all_flight_details)

    # today_rows = current_flight_details(db_config)
    # print(today_rows)
    # next_fly = next_flight_details(db_config)
    
    # print(next_fly)


