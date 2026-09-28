import time
import subprocess
import sys


CHECK_INTERVAL = 1800


# --------------------------------------------------
# RUN SCRIPT
# --------------------------------------------------

def run_script(script_name):

    print()
    print("=" * 60)
    print(f"Running {script_name}...")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, script_name]
    )

    if result.returncode != 0:

        print()
        print(
            f"{script_name} failed "
            f"with exit code {result.returncode}."
        )

        return False

    print()
    print(
        f"{script_name} finished successfully."
    )

    return True


# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def main():

    print()
    print("=" * 60)
    print("ANALYSIS LOOP STARTED")
    print("=" * 60)

    while True:

        print()
        print("Checking for articles requiring analysis...")

        # ------------------------------------------
        # 1. RUN ARTICLE ANALYSIS
        # ------------------------------------------

        success = run_script(
            "LLM_article_analysis.py"
        )

        if not success:

            print(
                "LLM analysis failed. "
                "Will retry later."
            )

        else:

            # --------------------------------------
            # 2. RUN FINAL SUMMARY
            # --------------------------------------

            success = run_script(
                "article_summary.py"
            )

            if not success:

                print(
                    "Finalization failed. "
                    "Will retry later."
                )

        # ------------------------------------------
        # 3. WAIT
        # ------------------------------------------

        print()
        print(
            f"Waiting {CHECK_INTERVAL} seconds "
            f"before checking again..."
        )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()