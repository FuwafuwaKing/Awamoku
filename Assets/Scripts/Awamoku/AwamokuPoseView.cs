using RosMessageTypes.Nav;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

namespace Awamoku
{
    public sealed class AwamokuPoseView : MonoBehaviour
    {
        [SerializeField] string odomTopic = "/odom";
        [SerializeField] float height = 0.35f;
        [SerializeField] float positionScale = 1f;

        void Start()
        {
            ROSConnection.GetOrCreateInstance().Subscribe<OdometryMsg>(odomTopic, OnOdom);
        }

        void OnOdom(OdometryMsg msg)
        {
            var pose = msg.pose.pose;
            var p = pose.position;
            var q = pose.orientation;
            transform.position = new Vector3(
                -(float)p.y * positionScale,
                height,
                (float)p.x * positionScale);
            transform.rotation = Quaternion.Euler(0f, -YawDegrees(q.x, q.y, q.z, q.w), 0f);
        }

        static float YawDegrees(double x, double y, double z, double w)
        {
            var sinyCosp = 2.0 * (w * z + x * y);
            var cosyCosp = 1.0 - 2.0 * (y * y + z * z);
            return Mathf.Rad2Deg * (float)System.Math.Atan2(sinyCosp, cosyCosp);
        }
    }
}
