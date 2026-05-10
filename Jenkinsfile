#!/usr/bin/env groovy
/**
 * finance_api_automation — Jenkins CI/CD Pipeline
 *
 * 支持功能：
 *   - 多环境切换（dev / test）
 *   - 测试标签过滤（smoke / regression / 全量）
 *   - pytest-xdist 并发执行
 *   - Allure 报告发布
 *   - ExtentReports HTML 报告生成与发布（pytest-html）
 *   - Coverage HTML 归档
 *   - 构建结果钉钉 / 邮件通知（按需开启）
 */

pipeline {

    // ─────────────────────── 执行节点 ───────────────────────
    agent any

    // ─────────────────────── 参数化构建 ─────────────────────
    parameters {
        choice(
            name: 'TEST_ENV',
            choices: ['test', 'dev'],
            description: '目标测试环境'
        )
        choice(
            name: 'TEST_MARK',
            choices: ['smoke', 'regression', 'account', 'payment', 'scenario', 'all'],
            description: '执行的测试标签；all 表示不过滤'
        )
        string(
            name: 'WORKERS',
            defaultValue: '1',
            description: 'pytest-xdist 并发进程数（1 表示串行）'
        )
        booleanParam(
            name: 'FAILFAST',
            defaultValue: false,
            description: '首次失败即停止（-x）'
        )
    }

    // ─────────────────────── 全局环境变量 ───────────────────
    environment {
        PYTHON_BIN    = 'python3'
        VENV_DIR      = "${WORKSPACE}/.venv"
        ALLURE_RESULTS = "${WORKSPACE}/outputs/allure_results"
        ALLURE_REPORT  = "${WORKSPACE}/outputs/allure_report"
        EXTENT_REPORT  = "${WORKSPACE}/outputs/extent_report"
        COVERAGE_HTML  = "${WORKSPACE}/outputs/coverage_html"
        LOG_DIR        = "${WORKSPACE}/outputs/logs"
        // 邮件通知收件人（多个地址用英文逗号分隔）
        NOTIFY_EMAIL   = 'qa-team@example.com'
    }

    // ─────────────────────── 超时与构建保留策略 ─────────────
    options {
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
        timestamps()
        ansiColor('xterm')
    }

    // ─────────────────────── 触发策略 ───────────────────────
    triggers {
        // 每天凌晨 2:00 自动执行回归（可按需修改或删除）
        cron('H 2 * * *')
    }

    // ═════════════════════ S T A G E S ══════════════════════
    stages {

        // ── 1. 拉取代码 ──────────────────────────────────────
        stage('Checkout') {
            steps {
                echo ">>> 分支: ${env.GIT_BRANCH ?: 'N/A'} | 环境: ${params.TEST_ENV} | 标签: ${params.TEST_MARK}"
                checkout scm
            }
        }

        // ── 2. 准备 Python 虚拟环境 ──────────────────────────
        stage('Setup Python Env') {
            steps {
                sh """
                    echo "=== Python 版本 ==="
                    ${PYTHON_BIN} --version

                    echo "=== 创建虚拟环境 ==="
                    ${PYTHON_BIN} -m venv ${VENV_DIR}

                    echo "=== 升级 pip ==="
                    ${VENV_DIR}/bin/pip install --upgrade pip --quiet

                    echo "=== 安装依赖 ==="
                    ${VENV_DIR}/bin/pip install -r requirements.txt --quiet

                    echo "=== 安装 pytest-html（ExtentReports）==="
                    ${VENV_DIR}/bin/pip install pytest-html --quiet
                """
            }
        }

        // ── 3. 初始化输出目录 ─────────────────────────────────
        stage('Prepare Dirs') {
            steps {
                sh """
                    mkdir -p ${ALLURE_RESULTS}
                    mkdir -p ${ALLURE_REPORT}
                    mkdir -p ${EXTENT_REPORT}
                    mkdir -p ${COVERAGE_HTML}
                    mkdir -p ${LOG_DIR}
                """
            }
        }

        // ── 4. 执行自动化测试 ─────────────────────────────────
        stage('Run Tests') {
            steps {
                script {
                    // 构建 pytest 命令
                    def markOpt   = (params.TEST_MARK != 'all') ? "-m ${params.TEST_MARK}" : ''
                    def workerOpt = (params.WORKERS.toInteger() > 1) ? "-n ${params.WORKERS}" : ''
                    def failOpt   = params.FAILFAST ? '-x' : ''

                    // ExtentReports: pytest-html 生成独立 HTML 报告
                    def extentOpt = "--html=${env.EXTENT_REPORT}/report.html --self-contained-html"

                    def cmd = [
                        "${VENV_DIR}/bin/pytest",
                        markOpt,
                        workerOpt,
                        failOpt,
                        extentOpt
                    ].findAll { it }.join(' ')

                    echo ">>> 执行命令: ${cmd}"

                    withEnv(["TEST_ENV=${params.TEST_ENV}"]) {
                        // returnStatus=true：测试失败时不立即中断 Pipeline，交由后续阶段处理
                        def rc = sh(script: cmd, returnStatus: true)
                        env.TEST_EXIT_CODE = rc.toString()
                        echo ">>> pytest 退出码: ${rc}"
                    }
                }
            }
        }

        // ── 5. 生成 Allure 报告 ───────────────────────────────
        stage('Generate Allure Report') {
            steps {
                script {
                    // 若 Allure 可执行文件在 PATH 中则直接调用，否则跳过并警告
                    def allureExists = sh(
                        script: 'command -v allure >/dev/null 2>&1 && echo yes || echo no',
                        returnStdout: true
                    ).trim()

                    if (allureExists == 'yes') {
                        sh """
                            allure generate ${ALLURE_RESULTS} \
                                -o ${ALLURE_REPORT} \
                                --clean
                        """
                    } else {
                        echo "⚠️  allure 命令未找到，跳过报告生成（可在 Agent 上安装 allure-commandline）"
                    }
                }
            }
        }

        // ── 6. 发布 Allure 报告（需 Jenkins Allure 插件） ────
        stage('Publish Allure Report') {
            steps {
                script {
                    try {
                        allure([
                            includeProperties: false,
                            jdk              : '',
                            results          : [[path: 'outputs/allure_results']],
                            report           : 'outputs/allure_report'
                        ])
                    } catch (Exception e) {
                        echo "⚠️  Allure 插件未安装或配置异常，跳过发布: ${e.message}"
                    }
                }
            }
        }

        // ── 7. 发布 ExtentReport（需 Jenkins HTML Publisher 插件）────
        stage('Publish ExtentReport') {
            steps {
                script {
                    def reportFile = "${env.EXTENT_REPORT}/report.html"
                    def reportExists = sh(
                        script: "test -f '${reportFile}' && echo yes || echo no",
                        returnStdout: true
                    ).trim()

                    if (reportExists == 'yes') {
                        publishHTML(target: [
                            allowMissing         : false,
                            alwaysLinkToLastBuild: true,
                            keepAll              : true,
                            reportDir            : 'outputs/extent_report',
                            reportFiles          : 'report.html',
                            reportName           : 'ExtentReport',
                            reportTitles         : 'Finance API Test Report'
                        ])
                        echo "✅ ExtentReport 已发布: ${env.BUILD_URL}ExtentReport/"
                    } else {
                        echo "⚠️  outputs/extent_report/report.html 不存在，跳过 ExtentReport 发布"
                    }
                }
            }
        }

        // ── 8. 归档产物 ───────────────────────────────────────
        stage('Archive Artifacts') {
            steps {
                // 归档日志、覆盖率报告与 ExtentReport
                archiveArtifacts(
                    artifacts       : 'outputs/logs/**,outputs/coverage_html/**,outputs/extent_report/**',
                    allowEmptyArchive: true,
                    fingerprint      : true
                )
                // 发布 Coverage HTML（需 Jenkins HTML Publisher 插件）
                publishHTML(target: [
                    allowMissing         : true,
                    alwaysLinkToLastBuild: true,
                    keepAll              : true,
                    reportDir            : 'outputs/coverage_html',
                    reportFiles          : 'index.html',
                    reportName           : 'Coverage Report'
                ])
            }
        }

    } // end stages

    // ═════════════════════ P O S T ══════════════════════════
    post {

        always {
            echo ">>> 构建结束，清理临时文件"
            // 保留 outputs，仅清理虚拟环境（可按需注释掉以加速下次构建）
            sh "rm -rf ${VENV_DIR} || true"
        }

        success {
            echo "✅ 所有测试通过！"
            script { _notify('SUCCESS') }
        }

        unstable {
            echo "⚠️  部分测试未通过（UNSTABLE）"
            script { _notify('UNSTABLE') }
        }

        failure {
            echo "❌ 构建 / 测试失败！"
            script { _notify('FAILURE') }
        }

    }

} // end pipeline


// ═══════════════════ 通 知 函 数 ════════════════════════════

/**
 * 发送构建结果通知。
 * 默认使用邮件；如需钉钉，取消注释 DingTalk 块并填入 robotId。
 */
def _notify(String status) {
    def icon    = [SUCCESS: '✅', UNSTABLE: '⚠️', FAILURE: '❌'].getOrDefault(status, 'ℹ️')
    def subject = "${icon} [${status}] ${env.JOB_NAME} #${env.BUILD_NUMBER}"
    def body    = """
构建结果  : ${status}
任务名称  : ${env.JOB_NAME}
构建编号  : #${env.BUILD_NUMBER}
测试环境  : ${params.TEST_ENV}
测试标签  : ${params.TEST_MARK}
触发分支  : ${env.GIT_BRANCH ?: 'N/A'}
触发人    : ${env.BUILD_USER ?: 'Scheduler'}
构建地址  : ${env.BUILD_URL}
Allure   : ${env.BUILD_URL}allure/
Extent   : ${env.BUILD_URL}ExtentReport/
""".stripIndent()

    // ── 邮件通知（需 Email Extension 插件） ──────────────────
    try {
        emailext(
            to: "zhangkaiqi0612@163.com", // 直接写邮箱
            subject     : subject,
            body        : body,
            mimeType    : 'text/plain'
        )
    } catch (Exception e) {
        echo "⚠️  邮件通知发送失败（插件未安装？）: ${e.message}"
    }

    /* ── 钉钉通知（需 DingTalk 插件，填入 robotId 后取消注释） ──
    try {
        dingtalk(
            robot   : 'YOUR_DINGTALK_ROBOT_ID',
            type    : 'MARKDOWN',
            title   : subject,
            text    : ["${body.replace('\n', '\n\n> ')}"]
        )
    } catch (Exception e) {
        echo "⚠️  钉钉通知发送失败: ${e.message}"
    }
    */
}
