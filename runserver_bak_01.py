from flask import Flask
from flask import request
from maven_config import get_simple_maven_config
from npm_config import get_simple_npm_config
from default_config import get_simple_default_config
import json
from myjenkins import server
import logging
from log_util import logger
import traceback
import jenkins

log = logging.getLogger('mylogger')

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def webhook():
    """
    接收git提交参数，默认提交处理
    :return: 
    """
    # try:
    ret = request.data.decode('utf-8')
    # print(ret, type(ret))
    data = json.loads(ret)
    # git提交类型
    event = data['object_kind']
    print("event:", event)
    branch = data['ref']
    print(branch)
    branch_name = branch if branch.find('/') < 0 else branch[branch.rfind('/') + 1:]
    print('branch_name:', branch_name)
    git_url = data['project']['url']
    pro_name = "CI__" \
               + git_url[git_url.rfind(':') + 1:git_url.rfind("/")] + "__" \
               + git_url[git_url.rindex('/') + 1:git_url.rindex(".git")] + "__" + branch_name

    if event == 'push':
        if branch_name.startswith('release-'):
            create_build(data)
        elif branch_name.startswith('develop') and (request.args.get('dev') == '1' or request.args.get('dev') == 'true'):
            create_build(data)
        else:
            logger.error('未处理分支类型：[%s]！' % branch_name)
    elif event == 'tag_push':
        create_build(data)
    else:
        logger.error("未处理类型: [%s]！" % event)
    logger.info('已经完成对[%s]项目的创建！' % pro_name + '\n' + '分支/标签: [%s]' % branch_name)
    return 'Hello Webhook!'

    # except Exception as e:
    #     logger.error('创建[%s]失败!' % pro_name  + '\n' + '分支/标签: [%s]' % branch_name + '\n' + traceback.format_exc())
    #     return 'Hello Webhook!'


@app.route('/<j_n>', methods=['GET', 'POST'])
def webhook_jdk_npm(j_n):
    """
    接收git提交参数，处理以分支和url是jdk和npm类型
    :param j_n: 
    :return: 
    """
    # 获取JDK版本
    # try:
    # git提交信息
    ret = request.data.decode('utf-8')
    data = json.loads(ret)

    # git提交类型
    event = data['object_kind']
    branch = data['ref']
    branch_name = branch if branch.find('/') < 0 else branch[branch.rfind('/') + 1:]
    git_url = data['project']['url']
    pro_name = "CI__" \
               + git_url[git_url.rfind(':') + 1:git_url.rfind("/")] + "__" \
               + git_url[git_url.rindex('/') + 1:git_url.rindex(".git")] + "__" + branch_name
    if event == 'push':
        if branch_name.startswith('release-'):
            create_build(data, j_n)
        elif branch_name.startswith('develop') and (request.args.get('dev') == '1' or request.args.get('dev') == 'true'):
            create_build(data, j_n)
        else:
            logger.info('未处理分支类型：[%s]！' % branch_name)
            raise Exception('未处理分支类型：[%s]！' % branch_name)

    elif event == 'tag_push':
        if j_n.startswith('jdk') or j_n.startswith('npm'):
            create_build(data, j_n)
    else:
        logger.info("未处理类型: [%s]！" % event)
        raise Exception("未处理类型: [%s]！" % event)
    # logger.info('JSON_jdk_npm: [%s]' % ret)
    logger.info('已经完成对[%s]项目的构建！' % pro_name + '\n' + '分支/标签：[%s]' % branch_name)
    return 'Hello Webhook!'
    # except Exception as e:
    #     logger.error('创建[%s]失败：' % pro_name + '\n' + '分支/标签：[%s]' % branch_name + '\n' + traceback.format_exc())
    #     # return e
    #     return 'Hello Webhook!'


def create_build(data, project_type='default'):
    """
    构建默认提交类型
    :param data: 
    :param project_type: 
    :return: 
    """

    # try:
    git_url = data['project']['url']
    branch = data['ref']
    branch_name = branch if branch.find('/') < 0 else branch[branch.rfind('/') + 1:]
    pro_name = "CI__" \
               + git_url[git_url.rfind(':') + 1:git_url.rfind("/")] + "__" \
               + git_url[git_url.rindex('/') + 1:git_url.rindex(".git")] + "__" + branch_name

    if project_type == 'jdk7':
        build_name = 'JDK_7u79'
        config = get_simple_maven_config(url=git_url, branch=branch, jdk_version=build_name)
    elif project_type == 'jdk8':
        build_name = 'JDK_8u112'
        config = get_simple_maven_config(url=git_url, branch=branch, jdk_version=build_name)
    elif project_type == 'npm':
        config = get_simple_npm_config(url=git_url, branch=branch)
    elif not project_type or project_type == 'default':
        config = get_simple_default_config(url=git_url, branch=branch)
    else:
        logger.error('项目类型有误: [%s]' % project_type)
        # raise Exception("Project Type Error: [%s]" % project_type)
    s = 0
    while s < 20:
        s += 1
        try:
            if not server.get_job_name(pro_name):
                server.create_job(pro_name, config)
                logger.info('新的项目，开始创建[%s]项目名称！' % pro_name)
            else:
                logger.info('[%s]项目名称已存在，准备开始构建！' % pro_name)
            break
        except jenkins.JenkinsException as e:
            continue
    while s < 30:
        s += 1
        try:
            log.info("项目 [%s] 构建中..." % pro_name)
            server.build_job(pro_name)
            log.info("项目 [%s] 构建完成!" % pro_name)
            break
        except Exception as e:
            log.error("项目 [%s] 构建失败！" + '\n' + traceback.format_exc())
            continue

    # server.build_job(pro_name)
    logger.info('构建项目 [%s] 信息:' % pro_name + '分支/标签: [%s]' % branch_name + '构建重试次数：[%s]' % (s - 2))
    # except Exception as e:
    #     log.error('[%s]构建失败信息：' % pro_name + '分支/标签: [%s]' % branch_name + '\n' + traceback.format_exc())


if __name__ == '__main__':
    app.run('0.0.0.0')
