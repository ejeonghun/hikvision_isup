# 요구사항 문서: 크로스 플랫폼 SDK 로더

## 소개

Hikvision ISUP 5.0 Python 프로젝트(`python_isup`)에서 Windows, Linux, macOS(aarch64) 환경을 자동으로 감지하고 적절한 네이티브 SDK 라이브러리를 로드하는 크로스 플랫폼 SDK 로더 기능을 구현한다. 현재 코드는 Windows DLL 경로가 하드코딩되어 있고, Linux/macOS 지원이 부분적이며, macOS용 네이티브 SDK가 존재하지 않는 상황이다. 개발팀이 macOS를 사용하므로 에뮬레이션 또는 호환성 레이어를 통한 macOS 개발 환경 지원이 필요하다.

## 용어 정의

- **SDK_Loader**: 플랫폼을 감지하고 적절한 네이티브 라이브러리를 로드하는 모듈
- **Platform_Detector**: 현재 실행 환경의 OS 종류와 CPU 아키텍처를 감지하는 컴포넌트
- **Library_Resolver**: 플랫폼에 맞는 SDK 라이브러리 파일 경로를 탐색하고 결정하는 컴포넌트
- **Compatibility_Layer**: macOS에서 네이티브 SDK가 없을 때 Linux SDK를 에뮬레이션하거나 스텁을 제공하는 호환성 계층
- **SDK_Directory**: SDK 공유 라이브러리 파일들이 위치한 디렉토리 (Windows: `include/lib64`, Linux: `include/linux`)
- **CMS_Library**: `HCISUPCMS.dll` / `libHCISUPCMS.so` — ISUP CMS 관리 라이브러리
- **Stream_Library**: `HCISUPStream.dll` / `libHCISUPStream.so` — ISUP 스트림 관리 라이브러리
- **Stub_Library**: macOS 개발 환경에서 SDK 함수 시그니처만 제공하고 실제 동작은 하지 않는 대체 라이브러리
- **Platform_Config**: 플랫폼별 라이브러리 이름, 경로 패턴, 의존성 정보를 담은 설정 구조체

## 요구사항

### 요구사항 1: 플랫폼 자동 감지

**사용자 스토리:** 개발자로서, 서버 실행 시 현재 OS와 아키텍처를 자동으로 감지하여 수동 설정 없이 적절한 SDK가 로드되기를 원한다.

#### 인수 조건

1. WHEN 서버가 시작될 때, THE Platform_Detector SHALL 현재 OS(Windows, Linux, macOS)와 CPU 아키텍처(x86_64, aarch64)를 감지하여 반환한다
2. THE Platform_Detector SHALL 감지된 플랫폼 정보를 `(os_name, architecture)` 튜플 형태로 제공한다
3. WHEN 지원되지 않는 OS 또는 아키텍처가 감지될 때, THE Platform_Detector SHALL 지원 플랫폼 목록을 포함한 명확한 오류 메시지를 반환한다
4. THE Platform_Detector SHALL `platform` 및 `os` 표준 라이브러리만 사용하여 플랫폼을 감지한다

### 요구사항 2: 플랫폼별 SDK 디렉토리 매핑

**사용자 스토리:** 개발자로서, 각 플랫폼에 맞는 SDK 디렉토리가 자동으로 선택되어 환경변수를 매번 설정하지 않아도 되기를 원한다.

#### 인수 조건

1. WHEN Windows 플랫폼이 감지될 때, THE Library_Resolver SHALL `include/lib64` 디렉토리를 기본 SDK_Directory로 선택한다
2. WHEN Linux 플랫폼이 감지될 때, THE Library_Resolver SHALL `include/linux` 디렉토리를 기본 SDK_Directory로 선택한다
3. WHEN macOS 플랫폼이 감지될 때, THE Library_Resolver SHALL Compatibility_Layer 경로를 기본 SDK_Directory로 선택한다
4. WHEN `HCISUP_SDK_DIR` 환경변수가 설정되어 있을 때, THE Library_Resolver SHALL 환경변수 값을 자동 감지된 경로보다 우선하여 사용한다
5. WHEN 선택된 SDK_Directory가 존재하지 않을 때, THE Library_Resolver SHALL 탐색한 경로 목록을 포함한 오류 메시지를 반환한다

### 요구사항 3: 플랫폼별 라이브러리 파일명 매핑

**사용자 스토리:** 개발자로서, 플랫폼에 따라 올바른 라이브러리 파일명(.dll, .so, .dylib)이 자동으로 결정되기를 원한다.

#### 인수 조건

1. WHEN Windows 플랫폼일 때, THE Library_Resolver SHALL CMS_Library를 `HCISUPCMS.dll`, Stream_Library를 `HCISUPStream.dll`로 매핑한다
2. WHEN Linux 플랫폼일 때, THE Library_Resolver SHALL CMS_Library를 `libHCISUPCMS.so`, Stream_Library를 `libHCISUPStream.so`로 매핑한다
3. WHEN macOS 플랫폼일 때, THE Library_Resolver SHALL CMS_Library를 `libHCISUPCMS.dylib` 또는 `libHCISUPCMS.so` 순서로 탐색한다
4. THE Library_Resolver SHALL OpenSSL 의존성 라이브러리도 플랫폼에 맞게 매핑한다 (Windows: `libeay32.dll`/`ssleay32.dll`, Linux: `libcrypto.so`/`libssl.so`)
5. WHEN `HCISUPCMS_PATH` 또는 `HCISUPSTREAM_PATH` 환경변수가 설정되어 있을 때, THE Library_Resolver SHALL 해당 환경변수 값을 자동 매핑보다 우선하여 사용한다

### 요구사항 4: Windows DLL 의존성 경로 관리

**사용자 스토리:** 개발자로서, Windows에서 SDK DLL의 의존성 라이브러리(HCAapSDKCom 등)가 자동으로 검색 경로에 추가되기를 원한다.

#### 인수 조건

1. WHILE Windows 플랫폼에서 실행 중일 때, THE SDK_Loader SHALL SDK_Directory와 `HCAapSDKCom` 하위 디렉토리를 DLL 검색 경로에 추가한다
2. WHILE Windows 플랫폼에서 실행 중일 때, THE SDK_Loader SHALL `os.add_dll_directory` API를 사용하여 DLL 검색 경로를 등록한다
3. WHILE Linux 또는 macOS 플랫폼에서 실행 중일 때, THE SDK_Loader SHALL Windows DLL 경로 등록 로직을 건너뛴다

### 요구사항 5: Linux SDK 로딩

**사용자 스토리:** 개발자로서, Linux 환경에서 `include/linux` 디렉토리의 `.so` 파일들이 올바르게 로드되기를 원한다.

#### 인수 조건

1. WHEN Linux 플랫폼이 감지될 때, THE SDK_Loader SHALL `ctypes.CDLL`을 사용하여 `.so` 라이브러리를 로드한다
2. WHEN Linux에서 SDK 라이브러리 로드에 실패할 때, THE SDK_Loader SHALL 누락된 의존성 라이브러리 정보를 포함한 오류 메시지를 반환한다
3. WHEN Linux 플랫폼일 때, THE SDK_Loader SHALL `HCAapSDKCom` 하위 디렉토리의 `.so` 파일들도 접근 가능하도록 `LD_LIBRARY_PATH` 설정 안내 또는 자동 경로 추가를 수행한다
4. THE SDK_Loader SHALL Linux에서 `ctypes.CFUNCTYPE`을 콜백 팩토리로 사용한다

### 요구사항 6: macOS 호환성 레이어

**사용자 스토리:** 개발자로서, macOS(aarch64)에서 네이티브 SDK가 없더라도 개발 및 코드 테스트가 가능하기를 원한다.

#### 인수 조건

1. WHEN macOS 플랫폼이 감지되고 네이티브 SDK 라이브러리가 존재하지 않을 때, THE Compatibility_Layer SHALL Stub_Library를 생성하여 SDK 함수 시그니처를 제공한다
2. THE Stub_Library SHALL CMS_Library와 Stream_Library의 모든 바인딩된 함수에 대해 호출 가능한 스텁을 제공한다
3. WHEN Stub_Library의 함수가 호출될 때, THE Stub_Library SHALL 해당 함수명과 인자를 로그로 출력하고 성공을 나타내는 기본 반환값을 반환한다
4. WHEN macOS에서 Stub_Library가 활성화될 때, THE SDK_Loader SHALL 시작 시 "macOS 스텁 모드: 실제 카메라 연동 불가" 경고 메시지를 출력한다
5. WHEN macOS에서 네이티브 SDK 라이브러리(.dylib 또는 .so)가 발견될 때, THE SDK_Loader SHALL Stub_Library 대신 네이티브 라이브러리를 로드한다

### 요구사항 7: 통합 설정 구조

**사용자 스토리:** 개발자로서, `config.py`의 플랫폼별 분기 로직이 SDK_Loader 모듈로 통합되어 설정 파일이 플랫폼 독립적이기를 원한다.

#### 인수 조건

1. THE SDK_Loader SHALL 플랫폼별 라이브러리 이름, 경로 패턴, 로더 타입, 콜백 팩토리를 Platform_Config 구조체로 캡슐화한다
2. THE SDK_Loader SHALL `config.py`에서 `IS_WINDOWS` 분기로 처리하던 라이브러리 경로 결정 로직을 대체한다
3. THE SDK_Loader SHALL Platform_Config를 통해 `LIB_LOADER`(WinDLL/CDLL)와 `CALLBACK_FACTORY`(WINFUNCTYPE/CFUNCTYPE)를 플랫폼에 맞게 제공한다
4. WHEN 새로운 플랫폼 지원이 추가될 때, THE SDK_Loader SHALL Platform_Config에 새 항목을 추가하는 것만으로 확장 가능한 구조를 제공한다

### 요구사항 8: SDK 로드 상태 진단

**사용자 스토리:** 개발자로서, SDK 로드 과정에서 발생하는 문제를 빠르게 진단할 수 있는 상세한 로그를 원한다.

#### 인수 조건

1. WHEN SDK 로드가 시작될 때, THE SDK_Loader SHALL 감지된 플랫폼, 선택된 SDK_Directory, 로드할 라이브러리 경로를 로그로 출력한다
2. WHEN SDK 라이브러리 로드에 성공할 때, THE SDK_Loader SHALL 로드된 라이브러리의 전체 경로와 로드 모드(네이티브/스텁)를 로그로 출력한다
3. IF SDK 라이브러리 로드에 실패할 때, THEN THE SDK_Loader SHALL OS 이름, 아키텍처, 시도한 경로 목록, 구체적인 오류 원인을 포함한 진단 메시지를 반환한다
4. WHEN 디버그 모드가 활성화되어 있을 때, THE SDK_Loader SHALL 라이브러리 탐색 과정의 각 단계를 상세히 로그로 출력한다

### 요구사항 9: 기존 코드 호환성 유지

**사용자 스토리:** 개발자로서, SDK 로더 리팩토링 후에도 기존 `run_isup_rtsp.py`의 모든 기능(RTSP, PTZ, 음성 전송)이 동일하게 동작하기를 원한다.

#### 인수 조건

1. THE SDK_Loader SHALL 기존 `IsupServer.__init__`에서 사용하는 `cms`와 `stream` 라이브러리 객체를 동일한 인터페이스로 제공한다
2. THE SDK_Loader SHALL 기존 `_bind_functions`에서 바인딩하는 모든 SDK 함수(NET_ECMS_*, NET_ESTREAM_*)가 정상적으로 호출 가능하도록 보장한다
3. THE SDK_Loader SHALL 기존 `AppConfig` 데이터클래스와의 호환성을 유지한다
4. THE SDK_Loader SHALL 기존 환경변수(`HCISUPCMS_PATH`, `HCISUPSTREAM_PATH`, `HCISUP_SDK_DIR`, `OPENSSL_LIBCRYPTO_PATH`, `OPENSSL_LIBSSL_PATH`) 오버라이드 동작을 유지한다
