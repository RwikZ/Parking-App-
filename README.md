This is the working project for IIT Madras BS Degree MAD 1 project(Aug 2025).

Problem Statement: Create a a multi-user app (one requires an administrator and other users) 
                   that manages different parking lots, parking spots and parked vehicles.
                   Assume that this parking app is for 4-wheeler parking.

Frameworks Used:  Flask (backend), Jinja 2 and HTML CSS ( Frontend) and SQLite (database).

Core Functionalities:
  Admin login and User login:
                            A login/register form with fields like username, password etc. for the user and a login form for the admin
                            You can either use a proper login framework or just use a simple HTML form with username and password (we are not concerned with how secure the login or the app is)
                            The app must have a suitable model to store and differentiate all types of users

  Admin Dashboard - for the Admin:
                                  The admin should be added, whenever a new database is created.
                                  The admin creates/edits/deletes a parking lot. Note: Delete only if all spots in the parking lot are empty.
                                  The admin can’t add each parking spot individually. The number of parking spots will be created based on the maximum number of parking spots in a lot.
                                  The admin can view the status of parking spot and check the parked vehicle details If the parking spot status is occupied.
                                  The admin can view all registered users.
                                  The admin can view the summary charts of parking lots/spots.

  User dashboard - for the User:
                                The user can choose an available parking lot and allocation is done as per the first available parking spot. Note: The user can’t select a parking spot.
                                The user changes the status of the parking spot to occupied, once the vehicle is parked.  
                                The user changes the parking spot status to released, once the vehicle is moved out of the parking.
                                The timestamp is recorded between parking in and parking out.
                                Shows the summary charts on his/her parking.

Extra / Optional Functionalities: 
                                  Ability for an admin to search for a particular parking spot and whether it is vacant or occupied.
                                  API resources are created to interact with the parkings spots, lots and/or users. (Mostly used CRUD: GET,POST,DELETE)
                                  External APIs/libraries for creating charts. (chart.js)
                                  Implementing frontend validation on all the form fields. (Used HTML Validations)
                                  Implement backend validation within your app's controllers.
                                  Provide styling and aesthetics to your application by creating a beautiful and responsive front end using simple CSS.
                    
