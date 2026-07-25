using System.Collections.Generic;
using RosMessageTypes.Geometry;
using RosMessageTypes.Nav;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;
using UnityEngine.UI;

namespace Awamoku
{
    public sealed class AwamokuDashboard : MonoBehaviour
    {
        static readonly HashSet<string> GameStates = new HashSet<string>
        {
            "IDLE", "PLAYING", "FINISHED", "EMERGENCY_STOP"
        };

        static readonly HashSet<string> CloudStates = new HashSet<string>
        {
            "DRIFT", "ATTRACT_RED", "ATTRACT_WHITE", "SHY_RED", "SHY_WHITE",
            "COMFORT_RED", "COMFORT_WHITE", "PANIC_RETURN", "COOLDOWN"
        };

        [Header("Publish topics")]
        [SerializeField] string redVoiceTopic = "/awamoku/red/voice_level_sim";
        [SerializeField] string whiteVoiceTopic = "/awamoku/white/voice_level_sim";
        [SerializeField] string commandTopic = "/awamoku/game/command";
        [SerializeField] float publishRateHz = 10f;

        [Header("UI")]
        [SerializeField] Slider redVoiceSlider;
        [SerializeField] Slider whiteVoiceSlider;
        [SerializeField] Text gameStateText;
        [SerializeField] Text cloudStateText;
        [SerializeField] Text targetTeamText;
        [SerializeField] Text redScoreText;
        [SerializeField] Text whiteScoreText;
        [SerializeField] Text redComfortText;
        [SerializeField] Text whiteComfortText;
        [SerializeField] Text timerText;
        [SerializeField] Text effectText;
        [SerializeField] Text rosPoseText;
        [SerializeField] Text unityPoseText;
        [SerializeField] Text desiredTwistText;
        [SerializeField] Text cmdVelText;
        [SerializeField] Transform cloudTransform;

        ROSConnection ros;
        float nextPublishTime;
        bool publishersRegistered;
        bool subscribersRegistered;
        bool publishErrorLogged;
        string gameState = "IDLE";
        string cloudState = "DRIFT";
        string targetTeam = "NONE";
        int redScore;
        int whiteScore;
        float redComfort;
        float whiteComfort;
        float timeRemaining = 75f;
        string effectMode = "NORMAL";
        bool hasOdom;
        bool hasDesiredTwist;
        bool hasCmdVel;
        float robotX;
        float robotY;
        float robotYawDeg;
        float desiredLinearX;
        float desiredAngularZ;
        float cmdLinearX;
        float cmdAngularZ;

        public void Configure(
            Slider redSlider,
            Slider whiteSlider,
            Text gameText,
            Text cloudText,
            Text targetText,
            Text redScore,
            Text whiteScore,
            Text redComfortLabel,
            Text whiteComfortLabel,
            Text timerLabel,
            Text effectLabel,
            Text rosPoseLabel,
            Text unityPoseLabel,
            Text desiredTwistLabel,
            Text cmdVelLabel,
            Transform cloud)
        {
            redVoiceSlider = redSlider;
            whiteVoiceSlider = whiteSlider;
            gameStateText = gameText;
            cloudStateText = cloudText;
            targetTeamText = targetText;
            redScoreText = redScore;
            whiteScoreText = whiteScore;
            redComfortText = redComfortLabel;
            whiteComfortText = whiteComfortLabel;
            timerText = timerLabel;
            effectText = effectLabel;
            rosPoseText = rosPoseLabel;
            unityPoseText = unityPoseLabel;
            desiredTwistText = desiredTwistLabel;
            cmdVelText = cmdVelLabel;
            cloudTransform = cloud;
            RefreshUi();
        }

        void Start()
        {
            EnsurePublishers();
            RegisterSubscribers();
            nextPublishTime = Time.time + 0.5f;
            RefreshUi();
        }

        void EnsurePublishers()
        {
            ros = ROSConnection.GetOrCreateInstance();
            if (publishersRegistered)
            {
                return;
            }
            ros.RegisterPublisher<Float32Msg>(redVoiceTopic);
            ros.RegisterPublisher<Float32Msg>(whiteVoiceTopic);
            ros.RegisterPublisher<StringMsg>(commandTopic);
            publishersRegistered = true;
        }

        void RegisterSubscribers()
        {
            if (subscribersRegistered)
            {
                return;
            }
            ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<StringMsg>("/awamoku/game/state", OnGameState);
            ros.Subscribe<StringMsg>("/awamoku/cloud/state", OnCloudState);
            ros.Subscribe<StringMsg>("/awamoku/cloud/target_team", msg => targetTeam = msg.data);
            ros.Subscribe<Int32Msg>("/awamoku/red/score", msg => redScore = msg.data);
            ros.Subscribe<Int32Msg>("/awamoku/white/score", msg => whiteScore = msg.data);
            ros.Subscribe<Float32Msg>("/awamoku/red/comfort", msg => redComfort = msg.data);
            ros.Subscribe<Float32Msg>("/awamoku/white/comfort", msg => whiteComfort = msg.data);
            ros.Subscribe<Float32Msg>("/awamoku/game/time_remaining", msg => timeRemaining = msg.data);
            ros.Subscribe<StringMsg>("/awamoku/effect/mode", msg => effectMode = msg.data);
            ros.Subscribe<OdometryMsg>("/odom", OnOdom);
            ros.Subscribe<TwistMsg>("/awamoku/motion/desired_twist", OnDesiredTwist);
            ros.Subscribe<TwistMsg>("/cmd_vel", OnCmdVel);
            subscribersRegistered = true;
        }

        void Update()
        {
            if (Time.time >= nextPublishTime)
            {
                PublishVoice();
                nextPublishTime = Time.time + 1f / Mathf.Max(0.1f, publishRateHz);
            }
            ApplyCloudPose();
            RefreshUi();
        }

        public void SendStart()
        {
            SendCommand("START");
        }

        public void SendReset()
        {
            SendCommand("RESET");
        }

        public void SendStop()
        {
            SendCommand("STOP");
        }

        public void SendEstop()
        {
            SendCommand("ESTOP");
        }

        void PublishVoice()
        {
            EnsurePublishers();
            if (ros == null || !publishersRegistered)
            {
                return;
            }
            var red = redVoiceSlider != null ? redVoiceSlider.value : 0f;
            var white = whiteVoiceSlider != null ? whiteVoiceSlider.value : 0f;
            try
            {
                ros.Publish(redVoiceTopic, new Float32Msg(Mathf.Clamp01(red)));
                ros.Publish(whiteVoiceTopic, new Float32Msg(Mathf.Clamp01(white)));
            }
            catch (System.Exception ex)
            {
                publishersRegistered = false;
                if (!publishErrorLogged)
                {
                    Debug.LogWarning($"Failed to publish Awamoku voice levels; will retry registration: {ex.Message}");
                    publishErrorLogged = true;
                }
            }
        }

        void SendCommand(string command)
        {
            EnsurePublishers();
            ros.Publish(commandTopic, new StringMsg(command));
        }

        void OnGameState(StringMsg msg)
        {
            if (!GameStates.Contains(msg.data))
            {
                Debug.LogError($"Unknown Awamoku game state: {msg.data}");
                return;
            }
            gameState = msg.data;
        }

        void OnCloudState(StringMsg msg)
        {
            if (!CloudStates.Contains(msg.data))
            {
                Debug.LogError($"Unknown Awamoku cloud state: {msg.data}");
                return;
            }
            cloudState = msg.data;
        }

        void OnOdom(OdometryMsg msg)
        {
            var pose = msg.pose.pose;
            robotX = (float)pose.position.x;
            robotY = (float)pose.position.y;
            robotYawDeg = YawDegrees(
                pose.orientation.x,
                pose.orientation.y,
                pose.orientation.z,
                pose.orientation.w);
            hasOdom = true;
        }

        void ApplyCloudPose()
        {
            if (!hasOdom || cloudTransform == null)
            {
                return;
            }
            cloudTransform.position = new Vector3(-robotY, cloudTransform.position.y, robotX);
            cloudTransform.rotation = Quaternion.Euler(0f, -robotYawDeg, 0f);
        }

        void OnDesiredTwist(TwistMsg msg)
        {
            desiredLinearX = (float)msg.linear.x;
            desiredAngularZ = (float)msg.angular.z;
            hasDesiredTwist = true;
        }

        void OnCmdVel(TwistMsg msg)
        {
            cmdLinearX = (float)msg.linear.x;
            cmdAngularZ = (float)msg.angular.z;
            hasCmdVel = true;
        }

        void RefreshUi()
        {
            SetText(gameStateText, $"Game: {gameState}");
            SetText(cloudStateText, $"Cloud: {cloudState}");
            SetText(targetTeamText, $"Target: {targetTeam}");
            SetText(redScoreText, $"Red Score: {redScore}");
            SetText(whiteScoreText, $"White Score: {whiteScore}");
            SetText(redComfortText, $"Red Comfort: {redComfort:0.00}");
            SetText(whiteComfortText, $"White Comfort: {whiteComfort:0.00}");
            SetText(timerText, $"Time: {timeRemaining:0.0}");
            SetText(effectText, $"Effect: {effectMode}");
            SetText(rosPoseText, hasOdom
                ? $"ROS Pose: x={robotX:0.00} y={robotY:0.00} yaw={robotYawDeg:0}"
                : "ROS Pose: waiting /odom");
            SetText(unityPoseText, cloudTransform != null
                ? $"Unity Cloud: x={cloudTransform.position.x:0.00} z={cloudTransform.position.z:0.00}"
                : "Unity Cloud: none");
            SetText(desiredTwistText, hasDesiredTwist
                ? $"Desired: v={desiredLinearX:0.00} w={desiredAngularZ:0.00}"
                : "Desired: waiting");
            SetText(cmdVelText, hasCmdVel
                ? $"CmdVel: v={cmdLinearX:0.00} w={cmdAngularZ:0.00}"
                : "CmdVel: waiting");
        }

        static void SetText(Text target, string value)
        {
            if (target != null)
            {
                target.text = value;
            }
        }

        static float YawDegrees(double x, double y, double z, double w)
        {
            var sinyCosp = 2.0 * (w * z + x * y);
            var cosyCosp = 1.0 - 2.0 * (y * y + z * z);
            return Mathf.Rad2Deg * (float)System.Math.Atan2(sinyCosp, cosyCosp);
        }
    }
}
