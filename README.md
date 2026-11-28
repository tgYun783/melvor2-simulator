# Melvor Idle 2 Simulator

Melvor Idle 2 (A RuneScape Adventure) 용 비공식 시뮬레이터입니다. 설치된 게임에서 데이터를, 로컬 세이브에서 캐릭터 상태를 읽어 브라우저 앱을 만들어 줍니다.

- **⚔ 전투 시뮬**: 현재 장비·레벨로 모든 적/던전을 몬테카를로 시뮬레이션해 시간당 처치 수, 전투 XP, 음식 소모, 사망 여부, 창고 가치 증감(드롭·GP·던전 보상 − 탄약·룬·음식 소모, 은행 판매가 기준)을 보여 줍니다. 장비·자세·음식·기도·전투 물약·점성술 노드를 바꿔 가며 비교할 수 있습니다. 기도와 물약은 세이브에 선택된 것이 기본값이며, 기도는 포인트와 관계없이 계속 유지된다고 가정하고, 시간당 기도 포인트(GP로 환산하지 않음)·기도 XP와 물약 소모량(판매가로 비용에 반영)을 보여 줍니다.
- **💰 수익성**: 벌목·채광·낚시·불피우기·요리·제련·화살 제작·공예·룬 제작·야수 공예·약초학·도둑질·농사·제분·목축의 모든 활동에 대해 시간당 창고 가치 증가량을 기대값으로 계산합니다. 재료 조달 방식(은행 판매가 / 상점 구매 / 직접 제작)과 툴벨트·스킬 음식 슬롯(도둑질 스시)·펫·길드 랭크·상점 업그레이드·화톳불·점성술·도둑질 방해 요소 보너스를 반영합니다. 도둑질 실패 HP 손실은 도둑질 음식 슬롯 음식의 소모량(HP 손실 ÷ 회복량)으로 바꿔 재료 비용에 넣습니다. 내용물이 고정된 상자는 열었다고 보고 계산합니다(Seaweed Clump → Seaweed 100개, Dock Waters·Sea Edge·Tuna Run 낚시터 특수 획득). 그래서 Seaweed가 필요한 요리·약초학 재료를 해당 낚시터에서 직접 조달하는 경로로 고를 수 있습니다. 제련의 희생 모루(Sacrificial Anvil, 점성술 Iridan Major 1) 옵션을 켜면 제품을 판매가 GP로 바꾼 기대값(GP·XP 각 ×1.05, 수집품 확률)으로 계산합니다.

## 실행 (배포본)

1. [Releases](../../releases) 에서 `Melvor2Simulator-<버전>.zip` 을 받습니다.
2. 게임 폴더 아래에 `mods\melvor2Simulator\` 폴더를 만들고 압축을 풉니다.
   기본 경로: `C:\Program Files (x86)\Steam\steamapps\common\Melvor Idle 2\mods\melvor2Simulator\`
3. `Melvor2Simulator.exe` 를 실행하면 최신 세이브를 읽어 `http://127.0.0.1:8765` 에 앱을 띄웁니다. 콘솔 창을 닫으면 종료됩니다.

첫 실행 때 `Melvor2.exe` 에서 게임 데이터(MelvorBase.json, 약 15 MB)를 추출하느라 몇 초 걸립니다. 게임이 업데이트되면 자동으로 다시 추출합니다.
게임 폴더에 쓰기 권한이 없으면 생성 파일은 `%LOCALAPPDATA%\Melvor2Simulator` 에 만들어집니다.

옵션: `--no-open`(브라우저 자동 열기 안 함), `--port 9000`, `--no-serve`(app.html 만 생성), `--cli --hours 2`(파이썬 전투 시뮬만 실행해 report.html 생성).

**업데이트**: 실행할 때 이 저장소의 최신 Release 를 확인하고(GitHub API 에 GET 한 번, 개인 정보 없음), 새 버전이 있으면 앱 상단에 안내가 뜹니다. "업데이트" 버튼을 누르면 zip 을 내려받아 실행 파일을 교체하고 자동으로 다시 시작합니다. 게임 폴더에 쓰기 권한이 없으면 버튼 대신 Release 링크가 보이니 직접 교체하세요. v0.1.0 에는 이 기능이 없어 한 번은 직접 받아야 합니다.

Windows SmartScreen 경고가 뜰 수 있습니다. 서명되지 않은 PyInstaller 실행 파일이라 그렇습니다. 믿기 어려우면 아래처럼 소스로 실행하세요.

## 실행 (소스)

Python 3.12 에서 확인했습니다. 외부 패키지는 필요 없습니다. Brotli 압축 해제는 게임에 포함된 `System.IO.Compression.Native.dll` 을 ctypes 로 호출합니다.

```powershell
python melvor2_sim.py
```

이 폴더가 게임 폴더 아래(`<게임 폴더>\Melvor2Sim` 또는 `<게임 폴더>\mods\<이름>`)에 있어야 합니다. 다른 곳이면 환경변수 `MELVOR2_DIR` 에 게임 폴더 경로를 넣어 주세요.

## 빌드

```powershell
python -m pip install pyinstaller
python build_exe.py
```

`<게임 폴더>\mods\melvor2Simulator\Melvor2Simulator.exe` 와 `README.txt` 가 만들어집니다. 템플릿(`app_template.html`, `profit.js`, `profit.css`)은 exe 에 내장되며, 같은 이름의 파일을 exe 옆에 두면 그 파일이 우선합니다.

## 동작 방식

- 게임 데이터: `Melvor2.exe` 안의 Godot PCK 섹션에서 `Data/Packages/MelvorBase.json` 을 꺼내 `cache/` 에 저장합니다. 게임 파일은 읽기만 합니다.
- 세이브: `%APPDATA%\Games By Malcs\Melvor Idle 2\steam\<steamid>\saves\` 의 가장 최근 `.sav` 를 읽습니다(Brotli + .NET BinaryWriter 형식). 쓰지 않습니다.
- 공식: 디컴파일한 게임 코드와 대조해 맞춘 수식을 사용합니다(명중/회피 레이팅, 최대 타격, 스킬 행동 간격, 성공률, 도둑질 실패 피해·기절 등).
- 앱의 "↺ 세이브 갱신" 버튼은 로컬 서버가 떠 있을 때 최신 세이브를 다시 읽습니다.

## 반영하지 않는 것

기도·물약의 반사·조건부(슬레이어 과제 등) 효과, 플레이어 Armour·Ward(Zenith 등), 장비 고유 효과 대부분, TurnCounting 계열 적 패시브, 탄약·룬 소모와 보존, 소모성 툴벨트 아이템 비용, 낚시 미끼, 사냥·민첩, 판매가 수정치, 조건부 보너스, 점성술 전투 효과 노드. 도둑질 HP 자연 회복·자동식사 효율·과회복.

## 주의

비공식 팬 도구이며 Games by Malcs / Jagex 와 무관합니다. 게임 데이터는 저장소와 배포본에 포함하지 않고 사용자의 설치본에서 실행 시 추출합니다. 생성되는 `app.html` 에는 본인 세이브 내용(캐릭터 이름, 은행 등)이 들어 있으니 공유하지 마세요.
