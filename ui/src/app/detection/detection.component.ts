import { Component, OnInit } from '@angular/core';
import { ApiService } from '../api.service';
import { Observable } from 'rxjs';
import { FormBuilder } from '@angular/forms';

@Component({
  selector: 'app-detection',
  templateUrl: './detection.component.html',
  styleUrls: ['./detection.component.scss'],

})
export class DetectionComponent implements OnInit {
  aliveStatus: Observable<any>;
  messages: Observable<any>;
  chatroomForm;
  results = {
    total: 3,
    crypto: 2,
    giardia: 0,
    beads: 1
  }

  constructor(private apiService: ApiService, private formBuilder: FormBuilder) {
    this.chatroomForm = this.formBuilder.group({
      content: ''
    });
  }

  ngOnInit() {
    this.aliveStatus = this.apiService.getAliveStatus();
    this.aliveStatus.subscribe((foo) => console.log(foo))

    this.messages = this.apiService.getMessage()
    this.messages.subscribe((foo) => console.log(`messages ${foo}`))
  }

  onSubmit(message) {
    console.log(`Submitted message`, message);
    this.apiService.sendMessage(message.content)
    this.chatroomForm.reset();
  }

}
