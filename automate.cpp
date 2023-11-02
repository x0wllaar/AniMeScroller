#include<iostream>
#include<string>
using namespace std;
int main(void){
	string buffer;
	cout<<"Enter the Text : ";
	getline(cin, buffer, '\n');
	string str = "./generate_gif.py -t \"";
	str = str + buffer + "\" -o scroll.gif";
	float scale;
	cout<<"Scale : ";
	cin>>scale;
	const char* command = str.c_str();
	system(command);
	str = "asusctl anime gif -p scroll.gif -l 0 -a 0.65 -s " + to_string(scale);
	command = str.c_str();
	system(command);

}
