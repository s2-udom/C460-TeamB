import {
to = aws_instance.jenkins_controller
id = "i-0702ad709c3e74a9f"
}

import {
to = aws_instance.jenkins_agent
id = "i-0b3687f4753806218"
}
import {
to = aws_security_group.jenkins_controller
id = "sg-0c60abd851d23a3a1"
}
