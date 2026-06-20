import argparse


# فرض کنید که StrategyLoader از کد قبلی استفاده می‌کنید

def parse_arguments():
    # ایجاد یک پارسر برای ورودی‌ها
    parser = argparse.ArgumentParser(description="بارگذاری استراتژی‌ها از پلاگین‌ها")

    # تعریف پارامترهای ورودی
    parser.add_argument(
        "--generate",
        type=str,
        required=True,
        help="استراتژی"
    )
    parser.add_argument(
        "--cache",
        type=bool,
        default=False,
        help="آیا کش فعال است؟ (True یا False)"
    )

    parser.add_argument(
        "--symbol_db",
        type=str,
        default="BTC",
        help="database name"
    )

    parser.add_argument(
        "--tick",
        type=int,
        default="5",
        help="ticket size"
    )

    parser.add_argument(
        "--def_stop",
        type=float,
        default="0.003",
        help="wrong stop for Short or Long this stop"
    )

    parser.add_argument(
        "--db_type",
        type=str,
        default="sqlite",
        help="type database"
    )
    parser.add_argument(
        "--def_tp",
        type=float,
        default="0.003",
        help="wrong tp for Short or Long this stop"
    )


    # دریافت ورودی‌ها از خط فرمان
    return parser.parse_args()

