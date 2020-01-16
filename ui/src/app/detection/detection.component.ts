import { Component, OnInit } from '@angular/core';
import { ApiService } from '../api.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-detection',
  templateUrl: './detection.component.html',
  styleUrls: ['./detection.component.scss'],

})
export class DetectionComponent implements OnInit {
  aliveStatus: Observable<any>;

  constructor(private apiService: ApiService) { }

  ngOnInit() {
    this.aliveStatus = this.apiService.getAliveStatus();
    this.aliveStatus.subscribe((foo) => console.log(foo))
  }

}
