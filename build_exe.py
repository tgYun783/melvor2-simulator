# -*- coding: utf-8 -*-
"""Package melvor2_sim.py as a single executable in <game>/mods/melvor2Simulator/.

    python build_exe.py            # builds Melvor2Simulator.exe (needs: python -m pip install pyinstaller)

The exe bundles app_template.html / profit.js / profit.css; a copy of any of those placed next to the
exe overrides the bundled one (handy for tweaking the UI without rebuilding). The exe writes app.html,
cache/ and results next to itself and finds the game folder by walking up until it sees Melvor2.exe.
"""
import io, os, re, shutil, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)
OUT_DIR = os.path.join(GAME_DIR, "mods", "melvor2Simulator")
NAME = "Melvor2Simulator"
WORK = os.path.join(tempfile.gettempdir(), "melvor2sim_build")

def main():
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        raise SystemExit("PyInstaller가 없습니다:  python -m pip install pyinstaller")
    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.rmtree(WORK, ignore_errors=True)
    args = [
        os.path.join(HERE, "melvor2_sim.py"),
        "--onefile", "--console", "--clean", "--noconfirm",
        "--name", NAME,
        "--distpath", os.path.join(WORK, "dist"),
        "--workpath", os.path.join(WORK, "build"),
        "--specpath", os.path.join(WORK, "spec"),
    ]
    for f in ("app_template.html", "profit.js", "profit.css"):
        args += ["--add-data", os.path.join(HERE, f) + os.pathsep + "."]
    print("PyInstaller", " ".join(args), flush=True)
    pyi.run(args)
    staged = os.path.join(WORK, "dist", NAME + ".exe")
    # release zip (exe + README.txt, no game data) in Melvor2Sim/dist — this is what goes on the GitHub Release
    ver = re.search(r'^VERSION = "([^"]+)"', io.open(os.path.join(HERE, "melvor2_sim.py"), encoding="utf-8").read(), re.M).group(1)
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    zpath = os.path.join(HERE, "dist", f"{NAME}-v{ver}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(staged, NAME + ".exe"); zf.writestr("README.txt", README)
    print(f"배포 zip: {zpath}  ({os.path.getsize(zpath) / 1e6:.1f} MB)", flush=True)
    try:
        shutil.copy2(staged, os.path.join(OUT_DIR, NAME + ".exe"))
    except PermissionError:
        raise SystemExit(f"\n{NAME}.exe 가 실행 중이라 교체할 수 없습니다. 실행 중인 시뮬레이터 창을 닫고 다시 빌드하세요.\n"
                         f"(빌드된 파일: {staged})")

    # seed the data cache so the first start does not have to extract MelvorBase.json again
    src = os.path.join(HERE, "cache", "MelvorBase.json")
    if os.path.exists(src):
        os.makedirs(os.path.join(OUT_DIR, "cache"), exist_ok=True)
        shutil.copy2(src, os.path.join(OUT_DIR, "cache", "MelvorBase.json"))
    with open(os.path.join(OUT_DIR, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(README)
    exe = os.path.join(OUT_DIR, NAME + ".exe")
    print(f"\n완료: {exe}  ({os.path.getsize(exe) / 1e6:.1f} MB)")

README = """Melvor Idle 2 시뮬레이터 (Melvor2Simulator.exe)
================================================

실행: Melvor2Simulator.exe 를 더블클릭합니다.
  - 최신 세이브를 읽어 app.html 을 만들고 http://127.0.0.1:8765 에서 열어 줍니다.
  - 콘솔 창을 닫으면 서버가 종료됩니다. 앱의 "↺ 세이브 갱신" 버튼은 이 서버가 떠 있을 때만 동작합니다.

옵션 (명령 프롬프트에서):
  Melvor2Simulator.exe --no-open          브라우저를 자동으로 열지 않음
  Melvor2Simulator.exe --port 9000        다른 포트 사용
  Melvor2Simulator.exe --no-serve         app.html 만 생성 (file:// 로 열기, 갱신 버튼 사용 불가)
  Melvor2Simulator.exe --cli --hours 2    파이썬 전투 시뮬만 실행 (report.html / results.json)

파일:
  app.html                 생성된 앱 (실행마다 덮어씀)
  cache/MelvorBase.json    Melvor2.exe 에서 추출한 게임 데이터 (게임이 업데이트되면 자동 재추출)
  app_template.html / profit.js / profit.css 를 이 폴더에 두면 내장된 것 대신 그 파일을 사용합니다.
  이 폴더에 쓰기 권한이 없으면(Program Files 아래 등) 위 파일들은 %LOCALAPPDATA%\\Melvor2Simulator 에 만들어집니다.
  콘솔 첫 줄에 어느 폴더를 쓰는지 표시됩니다.

이 폴더는 게임 폴더(Melvor2.exe 가 있는 곳) 아래에 있어야 합니다. 다른 곳에 둘 경우
환경변수 MELVOR2_DIR 에 게임 폴더 경로를 넣어 주세요.

세이브는 %APPDATA%\\Games By Malcs\\Melvor Idle 2 에서 읽기만 하며, 게임 파일과 세이브를 수정하지 않습니다.
비공식 팬 도구입니다. 게임 데이터는 배포본에 포함하지 않고 실행 시 설치된 게임에서 추출합니다.

소스 / 재빌드: README.md 참고 (python build_exe.py)
"""

if __name__ == "__main__":
    main()
