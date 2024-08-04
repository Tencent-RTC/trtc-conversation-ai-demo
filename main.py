

from tencentcloud.trtc.v20190722 import trtc_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common import credential
from flask import Flask, request, render_template
import json
import enum
import TLSSigAPIv2
import traceback
import loguru

from envyaml import EnvYAML

# read file env.yaml and parse config
env = EnvYAML('env.yaml')


cred = credential.Credential(
    env["CloudAPI.SECRET_ID"],
    env["CloudAPI.SECRET_KEY"])


httpProfile = HttpProfile()
httpProfile.endpoint = "trtc.tencentcloudapi.com"

clientProfile = ClientProfile()
clientProfile.httpProfile = httpProfile
# 实例化要请求产品的client对象,clientProfile是可选的
client = trtc_client.TrtcClient(cred, "ap-beijing", clientProfile)


def gen_user_sig(sdkappid, secret, userid):
    api = TLSSigAPIv2.TLSSigAPIv2(sdkappid, secret)
    sig = api.gen_sig(userid)
    return sig


app = Flask(__name__, static_folder="static")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


class ErrorCode(enum.Enum):
    InvalidParameter = "InvalidParameter"


def error_request(errcode, errmsg):
    return {
        "Response": {
            "Error": {
                "Code": errcode.name,
                "Message": errmsg
            },
        }
    }


action_list = [
    "join",
    "StartAITranscription",
    "StopAITranscription",
    "StartAIConversation",
    "StopAIConversation"
]


def handle_join(data):
    loguru.logger.info(f"handle_join recv json {data}")

    sdkappid = env["TRTC.SDKAPPID"]
    secret = env["TRTC.SECRET"]

    print(f"handle_join sdkappid={sdkappid} secret={secret}")

    userid = data["userid"]
    user_sig = gen_user_sig(sdkappid, secret, userid)
    robot_userid = data["robot_userid"]
    robot_user_sig = gen_user_sig(sdkappid, secret, robot_userid)

    rsp = {
        "sdkappid": sdkappid,
        "userid": userid,
        "usersig": user_sig,
        "robot_userid": robot_userid,
        "robot_usersig": robot_user_sig,
    }
    loguru.logger.info(f"handle_join send json {rsp}")
    return rsp


async def request_start_ai_conversation(body_json, action):

    body_json["LLMConfig"] = json.dumps(env["LLMConfig"])
    body_json["TTSConfig"] = json.dumps(env["TTSConfig"])

    loguru.logger.info(f"request_start_ai_conversation {body_json}")

    req = models.StartAIConversationRequest()
    params = {
        "SdkAppId": body_json["SdkAppId"],
        "RoomId": body_json["RoomId"],
        "AgentConfig": {
            "UserId": body_json["AgentConfig"]["UserId"],
            "UserSig": body_json["AgentConfig"]["UserSig"],
            "TargetUserId": body_json["AgentConfig"]["TargetUserId"],
        },
        "RoomIdType": 0,
        "STTConfig": {
            "Language": body_json["STTConfig"]["Language"],
        },
        "LLMConfig": body_json["LLMConfig"],
        "TTSConfig": body_json["TTSConfig"],
    }
    req.from_json_string(json.dumps(params))

    # 返回的resp是一个StartAIConversationResponse的实例，与请求对象对应
    resp = client.StartAIConversation(req)
    # 输出json格式的字符串回包
    return json.loads(resp.to_json_string())


async def request_stop_ai_conversation(body_json, action):

    req = models.StopAIConversationRequest()
    params = {
        "TaskId": body_json["TaskId"],
    }
    req.from_json_string(json.dumps(params))

    # 返回的resp是一个StopAIConversationResponse的实例，与请求对象对应
    resp = client.StopAIConversation(req)
    # 输出json格式的字符串回包
    print(resp.to_json_string())
    return json.loads(resp.to_json_string())


async def request_start_ai_transcription(body_json, action):

    req = models.StartAITranscriptionRequest()
    params = {
        "SdkAppId": body_json["SdkAppId"],
        "RoomId": body_json["RoomId"],
        "TranscriptionParams": {
            "UserId": body_json["TranscriptionParams"]["UserId"],
            "UserSig": body_json["TranscriptionParams"]["UserSig"],
        },
        "RoomIdType": 0,
        "RecognizeConfig": {
            "Language": body_json["RecognizeConfig"]["Language"],
        },
    }

    req.from_json_string(json.dumps(params))

    # 返回的resp是一个StartAITranscriptionResponse的实例，与请求对象对应
    resp = client.StartAITranscription(req)
    # 输出json格式的字符串回包
    return json.loads(resp.to_json_string())


async def request_stop_ai_transcription(body_json, action):

    req = models.StopAITranscriptionRequest()
    params = {
        "TaskId": body_json["TaskId"],
    }
    req.from_json_string(json.dumps(params))

    # 返回的resp是一个StopAITranscriptionResponse的实例，与请求对象对应
    resp = client.StopAITranscription(req)
    # 输出json格式的字符串回包
    return json.loads(resp.to_json_string())


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/conversation")
def conversation():
    return render_template('conversation.html')


@app.route("/transcription")
def transcription():
    return render_template('transcription.html')


@app.post("/action")
async def actions():

    action = ""
    body_json = request.json
    action = request.headers["Action"]

    if action not in action_list:
        return error_request(ErrorCode.InvalidParameter, f"action {action} invalid")

    body_json["Action"] = action

    try:
        if action == "join":
            loguru.logger.info(
                f"{request} {request.headers} {request.data}")
            return handle_join(body_json)
        elif action == "StartAIConversation":
            loguru.logger.info(
                f"{request} {request.headers} {body_json}")
            res = await request_start_ai_conversation(body_json, action)
            loguru.logger.info(f"ConversationAI {action} response {res}")
            print(f"ConversationAI {action} response {res}")
            return res
        elif action == "StopAIConversation":
            loguru.logger.info(
                f"{request} {request.headers} {request.data}")
            res = await request_stop_ai_conversation(body_json, action)
            loguru.logger.info(f"ConversationAI {action} response {res}")
            return res
        elif action == "StartAITranscription":
            loguru.logger.info(
                f"{request} {request.headers} {request.data}")
            res = await request_start_ai_transcription(body_json, action)
            print(f"ConversationAI {action} response {res}")
            return res
        elif action == "StopAITranscription":
            loguru.logger.info(
                f"{request} {request.headers} {request.data}")
            res = await request_stop_ai_transcription(body_json, action)
            return res
        else:
            return error_request(ErrorCode.InvalidParameter, f"action {action} invalid")
    except Exception as e:
        loguru.logger.info(
            f"ConversationAI {action} exception {traceback.format_exc()}")
        traceback.print_exc()
        return error_request(ErrorCode.InvalidParameter, str(e))


if __name__ == "__main__":
    loguru.logger.remove(0)
    loguru.logger.add("client.log", rotation="200 MB", retention=5)

    start_log = """
    ***************************************************************
                            start client.py
    ***************************************************************
    """
    loguru.logger.info(start_log)
    app.run("0.0.0.0", 8080)
