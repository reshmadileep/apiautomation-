pipeline{
    agent any
    stages{
        stage('Compile'){
	environment {
		PATH = "C:\\WINDOWS\\SYSTEM32"
		}
            steps{
		bat 'TestDeploy.bat'
                echo "Stage Complile Reached";
            }
        }
        stage('Build'){
            steps{
                echo "Stage Build Reached";
            }
        }
        stage('Test'){
            steps{
                echo "Stage Test Reached";
            }
        }
    }
    post{
        always {
            echo "This will always run";
        }
        success{
             echo "This will run when successful";
        }
        failure{
            echo "This will run when failed";
        }
        unstable{
            echo "This will run if the run was unstable.";
        }
    }
  
}
